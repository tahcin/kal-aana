"""Score each office: promise (official data) against reality (Google Maps listing and reviews).

Nothing here is a black box. Every score is a sum of named checks or a count of reviews, and
each carries the evidence behind it.

- Reachability (0-100): can a citizen reach the office through what Google shows them? Six
  checks with fixed points. A check that can't be decided ("n/a") is left out and the score
  is rescaled over the rest; the basis ("5 of 6 checks") is always shown with the score.
- Issue mix: how many of the office's recent reviews with text report each problem, counted
  over the same window for every office (the last ISSUE_WINDOW_DAYS), from the newest-first
  sample of its primary listing. Shown as counts with their denominator. Below MIN_SAMPLE
  reviews in the window the office is "insufficient evidence".
- Possible statutory breach: a review from the last RECENT_DAYS that reports a wait, for a
  service it names, at least 25% longer than that service's statutory timeline. Waits that
  went through an agent are set aside: the delay may be the agent's. Always worded
  "possible": a review is one person's account, and durations in reviews are approximate.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Final

from . import citizen, phones, taxonomy
from .collect import NEWEST
from .offices import CITIES, place_names
from .official import Office, OfficialData, Timeline
from .redact import safe_quote

ISSUE_WINDOW_DAYS: Final = 365  # issue shares count reviews from the last year only, for every office
MIN_SAMPLE: Final = 10  # reviews with text inside that window
MIN_PHONE_REPORTS: Final = 3  # reviews mentioning phones needed before "no one reports a failure" counts as a pass
RECENT_DAYS: Final = 730  # failed-call reports and breaches older than this aren't counted
QUOTES_PER_CATEGORY: Final = 3
WORKING_DAYS_PER_WEEK: Final = 5  # Sakala counts working days; reviewers count calendar days
BREACH_MARGIN: Final = 1.25  # reviewers count loosely ("about a month"): flag only clear overruns

GOV_SITE: Final = re.compile(r"^(?:https?://)?(?:[\w-]+\.)*(?:gov\.in|nic\.in)(?::\d+)?(?:[/?#]|$)", re.I)
_PHONING: Final = re.compile(
    r"\b(?:phones?|call(?:s|ed|ing)?|land\s?lines?|telephone|helpline|contact\s+numbers?|phone\s+numbers?)\b|ಫೋನ್|फ़ोन|फोन", re.I)
# A reviewer who used an agent: their wait (or unanswered call) may be the agent's doing.
_USED_AGENT: Final = re.compile(
    r"\b(?:through|via|hired|paid|gave\s+(?:it\s+)?to|booked|approached|contacted|engaged|took\s+help\s+(?:of|from))\s+"
    r"(?:an?\s+|the\s+|one\s+|some\s+|this\s+)?(?:agent|broker|middle\s?man|consultant|tout)s?\b"
    r"|\b(?:the|this|that|my)\s+(?:agent|broker|middle\s?man|consultant)\s+(?:told|said|promised|asked|charged|is|was|has|doesn'?t|won'?t)\b"
    r"|\bintroduced\s+(?:me\s+|us\s+)?to\s+(?:\w+\s+){0,2}(?:agent|broker)s?\b", re.I)


# What a quote, a check and a score look like


@dataclass(frozen=True)
class Quote:
    review_id: str
    text: str  # names and private mobiles masked
    evidence: str  # the matched words, verbatim (masked the same way)
    date: str  # YYYY-MM-DD
    rating: float | None
    link: str  # the review on Google Maps (unmasked there: it's the reviewer's public post)
    language: str
    sample: str  # NEWEST or "query:<keyword>"


@dataclass(frozen=True)
class Check:
    id: str
    label: str
    max_points: int
    passed: bool | None  # None: can't be decided, left out of the score
    detail: str

    @property
    def points(self) -> int:
        return self.max_points if self.passed else 0


@dataclass(frozen=True)
class Reachability:
    checks: tuple[Check, ...]

    @property
    def score(self) -> int | None:
        decided = [c for c in self.checks if c.passed is not None]
        possible = sum(c.max_points for c in decided)
        return round(100 * sum(c.points for c in decided) / possible) if possible else None

    @property
    def basis(self) -> str:
        decided = sum(c.passed is not None for c in self.checks)
        return f"{decided} of {len(self.checks)} checks"


@dataclass(frozen=True)
class IssueCount:
    category: str
    label: str
    polarity: taxonomy.Polarity
    count: int  # reviews in the window that report it
    of: int  # reviews with text in the window
    quotes: tuple[Quote, ...]  # from the window first, then older or keyword-found evidence

    @property
    def share(self) -> float | None:
        return self.count / self.of if self.of else None


@dataclass(frozen=True)
class Breach:
    service: Timeline
    reported_days: int  # calendar days, from the reviewer's words
    reported_working_days: int
    said: str  # the reviewer's own words for the duration, e.g. "almost a month"
    quote: Quote

    @property
    def explanation(self) -> str:
        return (f"Reviewer says \"{self.said}\" (about {self.reported_days} days, roughly {self.reported_working_days} "
                f"working days) for {self.service.name.lower()}; the Sakala timeline is {self.service.limit}.")


@dataclass(frozen=True)
class OfficeScore:
    office: Office
    listing: Mapping[str, Any] | None  # the primary Maps listing, as collected
    reachability: Reachability
    sample_size: int  # newest-first reviews of the primary listing (any date, with or without text)
    window_reviews: int  # of those, reviews with text inside the issue window: the denominator
    span: tuple[str, str] | None  # first and last date of the newest-first sample
    issues: tuple[IssueCount, ...]
    problem_reviews: int  # window reviews reporting at least one problem
    positive_reviews: int
    breaches: tuple[Breach, ...]  # possible breaches, last RECENT_DAYS, not through an agent
    agent_waits: tuple[Breach, ...]  # same, but the reviewer went through an agent
    older_breaches: int  # possible breaches reported before the RECENT_DAYS cut-off
    sampled: bool = True  # False when the collection didn't read this office's reviews (budget)

    @property
    def enough_evidence(self) -> bool:
        return self.window_reviews >= MIN_SAMPLE

    @property
    def problem_share(self) -> float | None:
        return self.problem_reviews / self.window_reviews if self.enough_evidence else None

    @property
    def positive_share(self) -> float | None:
        return self.positive_reviews / self.window_reviews if self.enough_evidence else None


# Helpers


def _date(iso: str | None) -> date | None:
    try:
        return datetime.fromisoformat((iso or "").replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _within(iso: str | None, as_of: date, days: int) -> bool:
    when = _date(iso)
    return when is not None and as_of - timedelta(days=days) <= when <= as_of


def _sample_of(review: Mapping[str, Any]) -> str:
    samples = review.get("samples") or [""]
    return NEWEST if NEWEST in samples else next((s for s in samples if s.startswith("query:")), samples[0])


def _reviews(n: int) -> str:
    return f"{n} review" if n == 1 else f"{n} reviews"


def _quote(review: Mapping[str, Any], hit: taxonomy.Hit, keep: frozenset[str]) -> Quote:
    source = review.get("text_original") if hit.source == "original" and review.get("text_original") else review["text"]
    return Quote(
        review_id=review["review_id"],
        text=safe_quote(source, keep),
        evidence=safe_quote(hit.text, keep),
        date=(review.get("iso_date") or "")[:10],
        rating=review.get("rating"),
        link=review.get("link", ""),
        language=hit.language,
        sample=_sample_of(review),
    )


# Durations and services named in reviews

_NUMBER_WORDS: Final = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve".split())} | {"a": 1, "an": 1}
# "(almost) 20 days", "a month", "1.5 months".
_DURATION: Final = re.compile(
    r"\b((?:almost|nearly|over|more\s+than|about|around|atleast|at\s+least)\s+)?"
    r"(\d{1,3}(?:\.\d)?|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a|an)\s*(days?|weeks?|months?)\b", re.I)
# A duration someone promised or a rule states isn't a wait: "will take 30 days", "within 7 days".
_PROMISE: Final = re.compile(
    r"\b(?:will\s+take|takes|within|in|promised|valid\s+for|tat\s+of|should\s+take|told\s+(?:me\s+)?(?:it\s+)?(?:will|would)\s+take)\s+$", re.I)
_UNIT_DAYS: Final = {"day": 1, "week": 7, "month": 30}

# Service mentions, most specific first. Ids are timeline ids in data/official. A cue with no
# id names a service without a statutory timeline in our data, so it can't be a breach.
# Short codes (LL, DL, RC, NOC, HP) are matched case-sensitively: "I'll" is not a learner's licence.
SERVICE_CUES: Final = (
    ("", r"\b(?:hyp\w*thec?\w*|(?-i:HP))\s+(?:termination|terminat\w*|cancel\w*|removal|remov\w*|closure)\b|(?-i:\bHP\b)\s+terminat\w*"),
    ("", r"(?-i:\bNOC\b)[^.!?]{0,15}?\bcancel\w*"),  # cancelling an NOC isn't the NOC issue service
    ("", r"\b(?:(?-i:RC)|registration|smart)\s+card\b"),  # a card in the post, not the service's decision
    ("", r"\baddress\s+change\b|\bchange\s+(?:of|in)\s+address\b"),  # not among the timelines we copied
    ("licence-renewal", r"(?-i:\bDL\b)\s+renew\w*|\blicen[cs]e\s+renew\w*|\brenew(?:al|ing|ed)?\s+(?:of\s+)?(?:my\s+|the\s+)?(?:(?-i:DL)|driving\s+licen[cs]e)\b"),
    ("rc-renewal", r"(?-i:\bRC\b)\s+renew\w*|\brenew(?:al|ing|ed)?\s+(?:of\s+)?(?:my\s+|the\s+)?(?:(?-i:RC)|registration)\b"),
    ("hypothecation", r"\bhyp\w*thec?\w*"),
    ("transfer-of-ownership", r"\b(?:ownership|name|(?-i:RC))\s+transfer\b|\btransfer\s+(?:of\s+)?(?:ownership|(?-i:RC)|vehicle)\b"),
    ("clearance-certificate", r"(?-i:\bNOC\b)"),
    ("learners-licence", r"(?-i:\bLL\b)|\blearner'?s?\b|\blearning\s+licen[cs]e\b"),
    ("driving-licence", r"(?-i:\bDL\b)|\bdriving\s+licen[cs]e\b"),
    ("vehicle-registration", r"\b(?:new|vehicle|bike|car)\s+registration\b|\bregistration\s+of\s+(?:my\s+|the\s+)?(?:new\s+)?(?:vehicle|bike|car)\b"),
)
_SERVICE_PATTERNS: Final = tuple((sid, re.compile(p, re.I)) for sid, p in SERVICE_CUES)


def reported_days(sentence: str) -> tuple[int, str] | None:
    """The longest wait a sentence reports, in calendar days, with the reviewer's words for it.
    Durations someone promised ("will take 30 days", "within 7 days") are ignored."""
    longest: tuple[int, str] | None = None
    for m in _DURATION.finditer(sentence):
        if _PROMISE.search(sentence[:m.start()]):
            continue
        amount, unit = m.group(2), m.group(3)
        n = float(amount) if amount[0].isdigit() else _NUMBER_WORDS[amount.lower()]
        days = round(n * _UNIT_DAYS[unit.lower().rstrip("s")])
        if longest is None or days > longest[0]:
            longest = (days, m.group(0).strip())
    return longest


def _first_service(text: str) -> str | None:
    """The most specific service cue in a text: a timeline id, "" for a service with no
    statutory timeline in our data, or None when no service is named."""
    for sid, pattern in _SERVICE_PATTERNS:
        if pattern.search(text):
            return sid
    return None


def service_named(sentence: str, review: str, timelines: Mapping[str, Timeline]) -> Timeline | None:
    """The service a delay is about: the one named in the delay's own sentence, or failing that,
    the only service the review names. Two different services and no clue which: None."""
    sid = _first_service(sentence)
    if sid is None:
        named = {s for s, p in _SERVICE_PATTERNS if p.search(review)}
        sid = named.pop() if len(named) == 1 else None
    return timelines.get(sid) if sid else None


def _sentence_around(text: str, start: int, end: int) -> str:
    left = max(text.rfind(c, 0, start) for c in ".!?\n") + 1
    rights = [i for i in (text.find(c, end) for c in ".!?\n") if i != -1]
    return text[left:min(rights) if rights else len(text)]


def possible_breach(review: Mapping[str, Any], hit: taxonomy.Hit, timelines: Mapping[str, Timeline],
                    keep: frozenset[str]) -> Breach | None:
    """A delay report whose duration clearly exceeds the statutory timeline of the service it names."""
    if hit.source != "text":  # durations and services are read in English
        return None
    text = review["text"]
    sentence = _sentence_around(text, hit.start, hit.end)
    found = reported_days(sentence)
    service = service_named(sentence, text, timelines)
    if found is None or service is None:
        return None
    days, said = found
    working = days * WORKING_DAYS_PER_WEEK // 7
    if working < service.days * BREACH_MARGIN:
        return None
    return Breach(service, days, working, said, _quote(review, hit, keep))


def went_through_agent(text: str) -> bool:
    return bool(_USED_AGENT.search(text.replace("\u2019", "'")))


# Reachability


def _reachability(office: Office, listing: Mapping[str, Any] | None, reviews: Sequence[Mapping[str, Any]],
                  data: OfficialData, city_std: str, as_of: date, searched: bool = True, sampled: bool = True) -> Reachability:
    if listing is None:
        how = "the Maps sweep or a targeted search" if searched else "the Maps sweep (no targeted search was run for it)"
        return Reachability((Check("listed", "Has a Google Maps listing of its own", 100, None,
                                   f"Not found by {how}. That isn't proof none exists, so the office isn't scored."),))
    phone = phones.parse(listing.get("phone_raw", ""))
    label_own = "The number shown is the office's own"
    if phone is None:
        own = Check("own_number", label_own, 20, None, "No number shown to check.")
    elif (verdict := citizen.classify(phone, office, data))[0] == "this office":
        own = Check("own_number", label_own, 20, True, f"{phone.display} is in the official directory.")
    elif verdict[0] == "national helpline":
        own = Check("own_number", label_own, 20, False,
                    f"{phone.display} is the {verdict[1]}, a national queue, not this office.")
    elif verdict[0] == "department helpline":
        own = Check("own_number", label_own, 20, False, f"{phone.display} is a department-wide helpline, not this office.")
    elif verdict[0] in ("regional office", "another office"):
        own = Check("own_number", label_own, 20, False, f"{phone.display} is {verdict[1]}, not this office's.")
    elif phone.area_code and phone.area_code != city_std:
        own = Check("own_number", label_own, 20, False,
                    f"{phone.display} has the STD code of {phone.region or phone.area_code}, not this city.")
    else:
        own = Check("own_number", label_own, 20, False, f"{phone.masked} is not in the official directory.")

    talks = [r for r in reviews if r["text"].strip() and _PHONING.search(r["text"] + " " + (r.get("text_original") or ""))]
    failed = []
    for r in talks:
        hit = taxonomy.classify(r["text"], r.get("text_original", ""), r.get("rating")).get("unreachable")
        # An agent who stops answering is not the office's phone.
        if hit and not (hit.source == "text" and "agent" in _sentence_around(r["text"], hit.start, hit.end).lower()):
            failed.append(r)
    failed.sort(key=lambda r: r.get("iso_date") or "", reverse=True)
    recent = [r for r in failed if _within(r.get("iso_date"), as_of, RECENT_DAYS)]
    label_through = f"No review in the last {RECENT_DAYS // 365} years reports failing to get through by phone"
    # One recent report of failing to get through fails the check; passing needs enough reviews
    # that mention phones, since silence from two reviews says little.
    if not sampled:
        through = Check("gets_through", label_through, 25, None, "Reviews were not read for this office, so this can't be checked.")
    elif recent:
        through = Check("gets_through", label_through, 25, False,
                        f"{_reviews(len(recent))} {'reports' if len(recent) == 1 else 'report'} they couldn't get through, most recently on {recent[0]['iso_date'][:10]}.")
    elif len(talks) < MIN_PHONE_REPORTS:
        through = Check("gets_through", label_through, 25, None,
                        f"{_reviews(len(talks))} {'mentions' if len(talks) == 1 else 'mention'} phones or calls (at least {MIN_PHONE_REPORTS} needed to pass).")
    else:
        older = f"; {_reviews(len(failed))} older than that do" if failed else ""
        through = Check("gets_through", label_through, 25, True, f"None of {_reviews(len(talks))} mentioning phones or calls do{older}.")

    website = listing.get("website", "")
    unclaimed = bool(listing.get("unclaimed"))
    return Reachability((
        Check("phone", "Google Maps shows a phone number", 25, phone is not None,
              (phone.display if phone.key in office.phone_keys or phone.key in data.national else phone.masked)
              if phone else "No phone on the listing citizens find first."),
        own,
        Check("website", "Links to a government website", 10, bool(GOV_SITE.search(website)),
              website or "No website on the listing."),
        Check("hours", "Shows opening hours", 10, bool(listing.get("has_hours")),
              "Hours listed." if listing.get("has_hours") else "No hours on the listing."),
        Check("claimed", "Managed by its owner on Google", 10, not unclaimed,
              "Google marks it unclaimed: no verified owner manages the listing."
              if unclaimed else "Not marked unclaimed."),
        through,
    ))


# Scoring an office


def score_office(office: Office, evidence: Mapping[str, Any], data: OfficialData, city: str, as_of: date) -> OfficeScore:
    primary_id = evidence.get("primary_id", "")
    listing = next((x for x in evidence.get("listings", []) if x["data_id"] == primary_id), None) if primary_id else None
    reviews = [r for r in evidence.get("reviews", []) if r["data_id"] == primary_id and r.get("text") is not None]
    # Place names of every office of this type stay readable in quotes: reviews compare offices.
    keep = frozenset(w for o in data.offices_of(office.office_type) for p in place_names(o) for w in p.split())
    timelines = {t.id: t for t in data.timelines_for(office.office_type)}

    sample = [r for r in reviews if NEWEST in (r.get("samples") or [])]
    window = [r for r in sample if r["text"].strip() and _within(r.get("iso_date"), as_of, ISSUE_WINDOW_DAYS)]
    window_ids = {r["review_id"] for r in window}
    hits = {r["review_id"]: taxonomy.classify(r["text"], r.get("text_original", ""), r.get("rating"))
            for r in reviews if r["text"].strip()}

    issues = []
    for category in taxonomy.CATEGORIES:
        counted = [r for r in window if category.id in hits[r["review_id"]]]
        others = [r for r in reviews if r["review_id"] not in window_ids and category.id in hits.get(r["review_id"], {})]
        ordered = sorted(counted, key=lambda r: r["iso_date"], reverse=True) + \
            sorted(others, key=lambda r: r.get("iso_date") or "", reverse=True)
        quotes = tuple(_quote(r, hits[r["review_id"]][category.id], keep) for r in ordered[:QUOTES_PER_CATEGORY])
        issues.append(IssueCount(category.id, category.label, category.polarity, len(counted), len(window), quotes))

    def reporting(polarity: str) -> int:
        return sum(any(taxonomy.BY_ID[c].polarity == polarity for c in hits[r["review_id"]]) for r in window)

    breaches, agent_waits, older = [], [], 0
    for r in reviews:
        hit = hits.get(r["review_id"], {}).get("delay")
        found = possible_breach(r, hit, timelines, keep) if hit else None
        if found is None:
            continue
        if not _within(r.get("iso_date"), as_of, RECENT_DAYS):
            older += 1
        elif went_through_agent(r["text"]):
            agent_waits.append(found)
        else:
            breaches.append(found)

    dates = sorted(r["iso_date"][:10] for r in sample if r.get("iso_date"))
    return OfficeScore(
        office=office,
        listing=listing,
        reachability=_reachability(office, listing, reviews, data, CITIES[city].std_code, as_of,
                                   searched=evidence.get("searched_individually", True),
                                   sampled=evidence.get("sampled", True)),
        sample_size=len(sample),
        window_reviews=len(window),
        span=(dates[0], dates[-1]) if dates else None,
        issues=tuple(issues),
        problem_reviews=reporting("problem"),
        positive_reviews=reporting("positive"),
        breaches=tuple(sorted(breaches, key=lambda b: b.quote.date, reverse=True)),
        agent_waits=tuple(sorted(agent_waits, key=lambda b: b.quote.date, reverse=True)),
        older_breaches=older,
        sampled=evidence.get("sampled", True),
    )


def score_collection(collection: Mapping[str, Any], data: OfficialData) -> list[OfficeScore]:
    """Score every office in a saved collection (data/collected/*.json), as of the day it was collected."""
    as_of = _date(collection["collected_at"][:10]) or date.today()
    return [score_office(data.offices[oid], ev, data, collection["city"], as_of) for oid, ev in collection["offices"].items()]
