"""Collect the evidence for one office type in one city, every response cached on disk.

The sweep, in the order credits are spent:

1. Google Maps search, up to `pages` pages per query: every listing citizens might find.
2. Match listings to the official directory (offices.match). No credits.
3. A targeted Maps search for each official office the sweep didn't confirm: no listing of
   its own matched on a phone number or the office code. Location-only matches can be a
   neighbouring duplicate, so they don't stop the search for the office's real listing.
4. Reviews of each office's primary listing (the most-reviewed listing that is the office):
   - newest first, tagged NEWEST, page by page until the sample holds `target_text` reviews
     with text or `newest_pages` pages have been read. (About two in three recent reviews are
     stars only, so busy offices need more pages.) This is the sample the issue mix is
     computed from: the office's most recent reviews, so every share is shown with its count
     and date range;
   - one keyword-filtered page per review query ("phone", "bribe", ...), tagged "query:...".
     These are biased on purpose: they find evidence, and never count towards shares. They
     are skipped when the newest-first pages already returned every review there is.
   The office's other listings (duplicates, test tracks) with at least
   `MIN_REVIEWS_FOR_SECONDARY` reviews get one newest-first page, tagged OTHER_LISTING.
   Private businesses trading on the office's name are reported, but not read.

Place details are not fetched: the Maps search result already carries the phone, hours and
"unclaimed" flag, and for RTO South it matched the place details call field for field.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Final

from .client import BudgetExceeded, CacheMiss, SearchClient, SearchError, SearchRecord
from .offices import CITIES, INDIA, OFFICE_TYPES, City, Listing, Match, MatchResult, OfficeType, match
from .official import Office, OfficialData
from .paths import DATA_DIR

COLLECTED_DIR: Final = DATA_DIR / "collected"
MAPS_PAGE_SIZE: Final = 20
REVIEWS_PAGE_SIZE: Final = 20  # the maximum `num`; Google's first newest-first page is fixed at up to 8
MIN_REVIEWS_FOR_SECONDARY: Final = 20

NEWEST: Final = "newest"  # the primary listing's newest reviews: the only sample shares come from
OTHER_LISTING: Final = "newest:other-listing"


class PartialCollection(RuntimeError):
    """Saving would overwrite a collection with one that a budget stop or error cut short."""


@dataclass(frozen=True)
class Review:
    """A Google Maps review. Reviewer names and profiles are deliberately not kept."""

    review_id: str
    data_id: str  # the listing it was left on
    rating: float | None
    iso_date: str
    text: str  # in English: Google's translation when it offers one, else the reviewer's words
    text_original: str  # the reviewer's own words, when `text` is a translation
    likes: int
    link: str  # the review on Google Maps: the evidence link
    samples: tuple[str, ...]  # NEWEST, OTHER_LISTING and/or "query:<keyword>"

    @classmethod
    def from_serpapi(cls, r: dict[str, Any], data_id: str, sample: str) -> Review:
        # SerpApi keeps the reviewer's words in `snippet` and, for a review Google translated,
        # adds `extracted_snippet.translated`.
        extracted = r.get("extracted_snippet") or {}
        original = r.get("snippet") or extracted.get("original") or ""
        text = extracted.get("translated") or original
        return cls(
            review_id=r["review_id"],
            data_id=data_id,
            rating=r.get("rating"),
            iso_date=r.get("iso_date", ""),
            text=text,
            text_original=original if original != text else "",
            likes=int(r.get("likes") or 0),
            link=r.get("link", ""),
            samples=(sample,),
        )


@dataclass
class OfficeEvidence:
    office_id: str
    listings: list[tuple[Listing, Match]] = field(default_factory=list)
    primary_id: str = ""  # data_id of the primary listing, "" if the office has no listing of its own
    reviews: dict[str, Review] = field(default_factory=dict)  # review_id -> review
    more_available: list[str] = field(default_factory=list)  # samples that stopped at a page limit
    sampled: bool = True  # False when the run read no reviews for this office (budget), so "no reviews" means "not read"
    searched: bool = False  # a targeted Maps search was run for this office

    def add(self, review: Review) -> None:
        seen = self.reviews.get(review.review_id)
        if seen is None:
            self.reviews[review.review_id] = review
        elif review.samples[0] not in seen.samples:
            self.reviews[review.review_id] = replace(seen, samples=(*seen.samples, *review.samples))

    def sample(self, name: str = NEWEST) -> list[Review]:
        return [r for r in self.reviews.values() if name in r.samples]

    def span(self, name: str = NEWEST) -> tuple[str, str]:
        """First and last review date (YYYY-MM-DD) in a sample, or ("", "") if it's empty."""
        dates = sorted(r.iso_date[:10] for r in self.sample(name) if r.iso_date)
        return (dates[0], dates[-1]) if dates else ("", "")


@dataclass
class Collection:
    office_type: str
    city: str
    collected_at: str
    offices: dict[str, OfficeEvidence]
    unmatched: list[tuple[Listing, str]]
    missing: list[str]  # official offices for which no listing of their own was found
    searches: list[SearchRecord]
    notes: list[str]  # what SerpApi said along the way, e.g. "no results"
    failures: list[str]  # searches that didn't happen: budget stop, cache miss, API error

    @property
    def fresh_searches(self) -> int:
        return sum(not s.cached for s in self.searches)

    def to_dict(self) -> dict[str, Any]:
        return {
            "office_type": self.office_type,
            "city": self.city,
            "collected_at": self.collected_at,
            "offices": {
                oid: {
                    "primary_id": ev.primary_id,
                    "sampled": ev.sampled,
                    "searched_individually": ev.searched,
                    "newest_span": ev.span(),
                    "more_available": ev.more_available,
                    "listings": [{**l.to_dict(), "match": asdict(m)} for l, m in ev.listings],
                    "reviews": [asdict(r) for r in ev.reviews.values()],
                }
                for oid, ev in self.offices.items()
            },
            "unmatched": [{**l.to_dict(), "why": why} for l, why in self.unmatched],
            "missing": self.missing,
            "searches": [{**asdict(s), "label": s.label} for s in self.searches],
            "notes": self.notes,
            "failures": self.failures,
        }

    def save(self, directory: Path = COLLECTED_DIR, allow_partial: bool = False) -> Path:
        if self.failures and not allow_partial:
            raise PartialCollection(f"{len(self.failures)} searches didn't run; not overwriting the saved collection")
        directory.mkdir(parents=True, exist_ok=True)
        suffix = "-partial" if self.failures else ""
        path = directory / f"{self.city.lower()}-{self.office_type}{suffix}.json"
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
        return path


# Request builders. Keeping them pure makes the plan (and its credit cost) inspectable.


def maps_search(query: str, city: City, page: int = 0) -> dict[str, Any]:
    params = {"engine": "google_maps", "type": "search", "q": query, "ll": city.ll, **INDIA}
    return {**params, "start": page * MAPS_PAGE_SIZE} if page else params


def reviews_newest(data_id: str, next_page_token: str = "") -> dict[str, Any]:
    params = {"engine": "google_maps_reviews", "data_id": data_id, "sort_by": "newestFirst", "hl": "en"}
    return {**params, "next_page_token": next_page_token, "num": REVIEWS_PAGE_SIZE} if next_page_token else params


def reviews_matching(data_id: str, keyword: str) -> dict[str, Any]:
    return {"engine": "google_maps_reviews", "data_id": data_id, "query": keyword, "num": REVIEWS_PAGE_SIZE, "hl": "en"}


def _listings(result: dict[str, Any], query: str) -> list[Listing]:
    search_id = result.get("search_metadata", {}).get("id", "")
    places = result.get("local_results") or []
    if not places and result.get("place_results"):  # Maps jumped straight to a single place
        places = [result["place_results"]]
    return [Listing.from_maps(p, query, search_id) for p in places if p.get("data_id")]


def _next_token(result: dict[str, Any]) -> str:
    return (result.get("serpapi_pagination") or {}).get("next_page_token", "")


class Collector:
    def __init__(self, client: SearchClient, official: OfficialData, office_type: OfficeType, city: City,
                 pages: int = 2, newest_pages: int = 4, target_text: int = 15, targeted: int | None = None,
                 sample_offices: int | None = None):
        self.client = client
        self.office_type = office_type
        self.city = city
        self.offices: list[Office] = official.offices_of(office_type.id)
        self.pages = pages
        self.newest_pages = newest_pages
        self.target_text = target_text
        self.targeted = targeted  # most targeted Maps searches (None: one per unconfirmed office)
        self.sample_offices = sample_offices  # read reviews for only the N most-reviewed offices
        self.notes: list[str] = []
        self.failures: list[str] = []
        self.searched: set[str] = set()  # offices that got a targeted Maps search

    def _search(self, params: dict[str, Any]) -> dict[str, Any] | None:
        """Run one search. A budget stop, cache miss or API error is recorded, never raised."""
        try:
            result = self.client.search(params)
        except (CacheMiss, BudgetExceeded, SearchError) as e:
            self.failures.append(str(e))
            return None
        if result.get("error"):  # e.g. "Google hasn't returned any results for this query."
            label = params.get("q") or params.get("query") or params.get("data_id", "")
            self.notes.append(f"{params['engine']} {label}: {result['error']}")
        return result

    def sweep_maps(self) -> list[Listing]:
        found: dict[str, Listing] = {}
        for query in self.office_type.maps_queries:
            for page in range(self.pages):
                result = self._search(maps_search(query, self.city, page))
                if result is None:
                    break
                listings = _listings(result, query)
                for listing in listings:
                    found.setdefault(listing.data_id, listing)
                if len(listings) < MAPS_PAGE_SIZE:
                    break
        return list(found.values())

    def confirm_offices(self, matched: MatchResult) -> None:
        """One targeted Maps search per official office without a strongly matched listing, offices
        with no listing at all first, up to `targeted` searches."""
        missing = {o.id for o in matched.missing(self.offices)}
        todo = sorted(matched.unconfirmed(self.offices), key=lambda o: o.id not in missing)
        for office in todo[:self.targeted]:
            self.searched.add(office.id)
            query = f"{self.office_type.search_prefix}{office.name}, {self.city.name}"
            result = self._search(maps_search(query, self.city))
            if result is None:
                continue
            known = {l.data_id for items in matched.matched.values() for l, _ in items}
            extra = match(_listings(result, query), [office], self.office_type)
            for listing, m in extra.matched.get(office.id, []):
                if listing.data_id not in known:
                    matched.matched.setdefault(office.id, []).append((listing, m))
                    matched.unmatched = [(l, why) for l, why in matched.unmatched if l.data_id != listing.data_id]

    def _read_newest(self, ev: OfficeEvidence, listing: Listing, sample: str, pages: int, target_text: int = 0) -> bool:
        """Read newest-first pages, stopping early once the sample holds `target_text` reviews
        with text. True only if every review Google counts for the listing has been read: Google
        sometimes ends newest-first paging early (after about 25 reviews on a busy listing)."""
        token = ""
        for _ in range(pages):
            result = self._search(reviews_newest(listing.data_id, token))
            if result is None:
                return False
            for r in result.get("reviews", []):
                ev.add(Review.from_serpapi(r, listing.data_id, sample))
            token = _next_token(result)
            if not token:
                return len(ev.sample(sample)) >= listing.reviews
            if target_text and sum(bool(r.text.strip()) for r in ev.sample(sample)) >= target_text:
                break
        ev.more_available.append(f"{sample} ({listing.title})")
        return False

    def _read_primary(self, ev: OfficeEvidence, listing: Listing) -> None:
        if self._read_newest(ev, listing, NEWEST, self.newest_pages, self.target_text):
            return  # every review is already in hand: keyword filters would only repeat them
        for keyword in self.office_type.review_queries:
            result = self._search(reviews_matching(listing.data_id, keyword))
            if result is None:
                continue
            for r in result.get("reviews", []):
                ev.add(Review.from_serpapi(r, listing.data_id, f"query:{keyword}"))
            if _next_token(result):
                ev.more_available.append(f"query:{keyword}")

    def run(self, reviews: bool = True) -> Collection:
        matched = match(self.sweep_maps(), self.offices, self.office_type)
        self.confirm_offices(matched)
        evidence: dict[str, OfficeEvidence] = {}
        listed = [o for o in self.offices if matched.primary(o.id)]
        busiest = sorted(listed, key=lambda o: -matched.primary(o.id).reviews)  # type: ignore[union-attr]
        sampled = {o.id for o in busiest[:self.sample_offices]} if reviews else set()
        for office in self.offices:
            primary = matched.primary(office.id)
            ev = OfficeEvidence(office.id, matched.listings_for(office.id), primary.data_id if primary else "",
                                sampled=office.id in sampled, searched=office.id in self.searched)
            evidence[office.id] = ev
            if not ev.sampled:
                continue
            for listing, m in ev.listings:
                if listing is primary:
                    self._read_primary(ev, listing)
                elif m.role != "private" and listing.reviews >= MIN_REVIEWS_FOR_SECONDARY:
                    self._read_newest(ev, listing, OTHER_LISTING, pages=1)
        return Collection(
            office_type=self.office_type.id,
            city=self.city.name,
            collected_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            offices=evidence,
            unmatched=matched.unmatched,
            missing=[o.id for o in matched.missing(self.offices)],
            searches=list(self.client.log),
            notes=self.notes,
            failures=self.failures,
        )


def collect(client: SearchClient, official: OfficialData, office_type: str, city: str, *,
            pages: int = 2, newest_pages: int = 4, target_text: int = 15, reviews: bool = True,
            targeted: int | None = None, sample_offices: int | None = None) -> Collection:
    collector = Collector(client, official, OFFICE_TYPES[office_type], CITIES[city], pages=pages,
                          newest_pages=newest_pages, target_text=target_text, targeted=targeted,
                          sample_offices=sample_offices)
    return collector.run(reviews)
