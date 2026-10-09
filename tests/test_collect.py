"""The collection sweep and the search client, with only SerpApi's HTTP call stubbed out.

The real SearchClient runs (cache, budget, dry run, error handling); `FakeSerpApi` stands in
for the `serpapi` package and serves hand-made responses. Every response here is a test
fixture shaped like SerpApi's JSON, not real data.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from kalaana import official
from kalaana.client import BudgetExceeded, CacheMiss, SearchClient, SearchError
from kalaana.collect import (
    NEWEST, OTHER_LISTING, Collection, Collector, PartialCollection, Review, maps_search, reviews_matching,
    reviews_newest,
)
from kalaana.offices import CITIES, OFFICE_TYPES

KA05 = "0xka05"
TRACK = "0xtrack"
AGENT = "0xagent"
KEY = "f" * 64
CITY = CITIES["Bengaluru"]


def review(rid: str, text: str = "") -> dict[str, Any]:
    return {"review_id": rid, "rating": 1.0, "iso_date": "2026-07-07T08:43:55Z", "snippet": text,
            "link": f"https://www.google.com/maps/reviews/data=!4m8!14m7!1m6!2m5!1s{rid}",
            "user": {"name": "A Reviewer", "link": "https://www.google.com/maps/contrib/1234567890", "contributor_id": "1234567890"}}


def place(data_id: str, title: str, reviews: int, **extra: Any) -> dict[str, Any]:
    return {"data_id": data_id, "title": title, "address": "Anjanapura, Bengaluru, Karnataka 560108",
            "type": "Department of motor vehicles", "reviews": reviews, **extra}


class FakeSerpApi:
    """Stands in for serpapi.Client: answers from canned responses, or with an empty result."""

    def __init__(self, responses: dict[str, dict[str, Any]]):
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def search(self, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(params)
        clean = {k: v for k, v in params.items() if k != "api_key"}
        return self.responses.get(json.dumps(clean, sort_keys=True), {})


def key(params: dict[str, Any]) -> str:
    return json.dumps(params, sort_keys=True)


def client_for(responses: dict[str, dict[str, Any]], cache_dir: Path, budget: int = 100) -> tuple[SearchClient, FakeSerpApi]:
    client = SearchClient(api_key=KEY, budget=budget, cache_dir=cache_dir)
    fake = FakeSerpApi(responses)
    client._client = fake  # only the HTTP layer is replaced
    return client, fake


@pytest.fixture
def responses() -> dict[str, dict[str, Any]]:
    page_one = [place(KA05, "Regional Transport Office (KA 05)", 240, unclaimed_listing=True),
                place(TRACK, "RTO KA 05 Driving Test Track", 40),
                place(AGENT, "Jayanagar RTO Services", 500, phone="98450 00000")]
    page_one += [place(f"0xfill{i}", f"Tea stall {i}", 1, type="Cafe") for i in range(17)]  # a full page of 20
    return {
        key(maps_search("Regional Transport Office", CITY)): {"local_results": page_one},
        key(maps_search("Regional Transport Office", CITY, page=1)): {"error": "Google hasn't returned any results for this query."},
        key(reviews_newest(KA05)): {"reviews": [review("r1", "No one picks up the phone"), review("r2")],
                                    "serpapi_pagination": {"next_page_token": "tok"}},
        key(reviews_newest(KA05, "tok")): {"reviews": [review("r3", "20 days and no LL approval")],
                                           "serpapi_pagination": {"next_page_token": "tok2"}},
        key(reviews_matching(KA05, "phone")): {"reviews": [review("r1", "No one picks up the phone"), review("r4", "landline dead")],
                                               "serpapi_pagination": {"next_page_token": "more"}},
        key(reviews_newest(TRACK)): {"reviews": [review("t1", "Test track was slow")]},
    }


def run(responses: dict[str, dict[str, Any]], cache_dir: Path, budget: int = 100) -> tuple[Collection, FakeSerpApi]:
    client, fake = client_for(responses, cache_dir, budget)
    collector = Collector(client, official.load(), OFFICE_TYPES["rto"], CITY, pages=2, newest_pages=2)
    return collector.run(), fake


# Request builders


def test_request_builders() -> None:
    assert reviews_newest("x") == {"engine": "google_maps_reviews", "data_id": "x", "sort_by": "newestFirst", "hl": "en"}
    assert reviews_newest("x", "t")["num"] == 20 and reviews_newest("x", "t")["next_page_token"] == "t"
    assert reviews_matching("x", "bribe") == {"engine": "google_maps_reviews", "data_id": "x", "query": "bribe", "num": 20, "hl": "en"}
    assert maps_search("RTO", CITY, page=1)["start"] == 20 and "start" not in maps_search("RTO", CITY)


# The sweep


def test_roles_and_what_gets_read(responses: dict[str, dict[str, Any]], tmp_path: Path) -> None:
    collection, fake = run(responses, tmp_path)
    ka05 = collection.offices["rto-ka05"]
    assert {l.data_id: m.role for l, m in ka05.listings} == {KA05: "office", TRACK: "facility", AGENT: "private"}
    assert ka05.primary_id == KA05
    asked = {p.get("data_id") for p in fake.calls}
    assert AGENT not in asked  # no credits spent on a private agent
    assert TRACK in asked  # a facility with 20+ reviews gets one page


def test_samples_are_kept_apart(responses: dict[str, dict[str, Any]], tmp_path: Path) -> None:
    collection, _ = run(responses, tmp_path)
    ka05 = collection.offices["rto-ka05"]
    assert {r.review_id for r in ka05.sample()} == {"r1", "r2", "r3"}  # the primary listing only
    assert ka05.reviews["r1"].samples == (NEWEST, "query:phone")
    assert ka05.reviews["r4"].samples == ("query:phone",)  # evidence only
    assert ka05.reviews["t1"].samples == (OTHER_LISTING,)  # the test track never enters the sample
    assert ka05.span() == ("2026-07-07", "2026-07-07")
    assert "query:phone" in ka05.more_available


def test_pagination_stops_and_errors_become_notes(responses: dict[str, dict[str, Any]], tmp_path: Path) -> None:
    collection, fake = run(responses, tmp_path)
    maps_calls = [p for p in fake.calls if p["engine"] == "google_maps" and p["q"] == "Regional Transport Office"]
    assert [p.get("start", 0) for p in maps_calls] == [0, 20]  # page 1 was full, so page 2 was asked for
    assert any("hasn't returned any results" in n for n in collection.notes)


def test_keyword_queries_skipped_only_when_every_review_is_in_hand(responses: dict[str, dict[str, Any]], tmp_path: Path) -> None:
    # Google ends paging after one review, but the listing has 240: keep searching by keyword.
    responses[key(reviews_newest(KA05))] = {"reviews": [review("r1", "fine")]}
    _, fake = run(responses, tmp_path / "a")
    assert [p for p in fake.calls if p.get("data_id") == KA05 and "query" in p]
    # A listing whose every review is already in hand needs no keyword searches.
    responses[key(maps_search("Regional Transport Office", CITY))]["local_results"][0]["reviews"] = 1
    _, fake = run(responses, tmp_path / "b")
    assert not [p for p in fake.calls if p.get("data_id") == KA05 and "query" in p]


def test_newest_sampling_stops_once_enough_reviews_have_text(responses: dict[str, dict[str, Any]], tmp_path: Path) -> None:
    client, fake = client_for(responses, tmp_path)
    Collector(client, official.load(), OFFICE_TYPES["rto"], CITY, pages=1, newest_pages=4, target_text=1).run()
    assert len([p for p in fake.calls if p.get("data_id") == KA05 and p.get("sort_by")]) == 1  # page 1 had a text review


def test_unconfirmed_offices_get_one_targeted_search(responses: dict[str, dict[str, Any]], tmp_path: Path) -> None:
    collection, fake = run(responses, tmp_path)
    targeted = [p["q"] for p in fake.calls if p["engine"] == "google_maps" and p["q"] != "Regional Transport Office"]
    rtos = official.load().offices_of("rto")
    assert len(targeted) == len(rtos) - 1  # KA-05 was confirmed by its office code
    assert "rto-ka59" in collection.missing and "rto-ka05" not in collection.missing


def test_reviewer_identity_is_not_kept(responses: dict[str, dict[str, Any]], tmp_path: Path) -> None:
    collection, _ = run(responses, tmp_path)
    saved = json.dumps(collection.to_dict())
    assert "A Reviewer" not in saved and "contrib" not in saved and "1234567890" not in saved


def test_partial_run_is_not_saved_over_a_full_one(responses: dict[str, dict[str, Any]], tmp_path: Path) -> None:
    collection, _ = run(responses, tmp_path / "cache", budget=3)
    assert any("budget" in f for f in collection.failures)
    with pytest.raises(PartialCollection):
        collection.save(tmp_path)
    assert collection.save(tmp_path, allow_partial=True).name == "bengaluru-rto-partial.json"


def test_translated_review_keeps_the_original() -> None:
    # Shape of a real translated review: the original in `snippet`, English in `translated`.
    r = Review.from_serpapi({"review_id": "k", "snippet": "ಕಳಪೆ ನಿರ್ವಹಣೆ",
                             "extracted_snippet": {"original": "ಕಳಪೆ ನಿರ್ವಹಣೆ", "translated": "Poor management"}}, "0x1", NEWEST)
    assert (r.text, r.text_original, r.samples) == ("Poor management", "ಕಳಪೆ ನಿರ್ವಹಣೆ", (NEWEST,))
    english = Review.from_serpapi({"review_id": "e", "snippet": "No one picks up", "extracted_snippet": {"original": "No one picks up"}}, "0x1", NEWEST)
    assert (english.text, english.text_original) == ("No one picks up", "")


# The search client


def test_cache_hit_costs_nothing(tmp_path: Path) -> None:
    client, fake = client_for({key({"engine": "google", "q": "x"}): {"organic_results": []}}, tmp_path)
    client.search({"engine": "google", "q": "x"})
    client.search({"engine": "google", "q": "x"})
    assert (client.spent, client.cache_hits, len(fake.calls)) == (1, 1, 1)
    assert [r.cached for r in client.log] == [False, True]
    client.search({"engine": "google", "q": "x"}, refresh=True)
    assert client.spent == 2


def test_budget_and_demo_mode(tmp_path: Path) -> None:
    client, _ = client_for({}, tmp_path, budget=1)
    client.search({"engine": "google", "q": "a"})
    with pytest.raises(BudgetExceeded):
        client.search({"engine": "google", "q": "b"})
    demo = SearchClient(api_key="", cache_dir=tmp_path)
    assert demo.demo_mode
    with pytest.raises(CacheMiss):
        demo.search({"engine": "google", "q": "c"})


def test_dry_run_counts_without_spending(tmp_path: Path) -> None:
    client = SearchClient(api_key="", cache_dir=tmp_path, dry_run=True)
    assert client.search({"engine": "google_maps", "q": "x"}) == {}
    assert client.spent == 0 and [r.cached for r in client.log] == [False]


def test_api_error_is_reported_without_the_key(tmp_path: Path) -> None:
    class Response:
        status_code = 400

        def json(self) -> dict[str, str]:
            return {"error": f"Invalid api_key={KEY}"}

    class Failing:
        def search(self, params: dict[str, Any]) -> dict[str, Any]:
            error = RuntimeError(f"400 for https://serpapi.com/search?api_key={KEY}")
            error.response = Response()  # type: ignore[attr-defined]
            raise error

    client = SearchClient(api_key=KEY, cache_dir=tmp_path)
    client._client = Failing()
    with pytest.raises(SearchError) as e:
        client.search({"engine": "google_maps", "q": "x"})
    assert KEY not in str(e.value) and "400" in str(e.value) and "Invalid" in str(e.value) and not e.value.retryable


@pytest.mark.parametrize(("status", "retryable"), [(None, True), (503, True), (429, False), (401, False)])
def test_only_timeouts_and_server_errors_are_worth_repeating(tmp_path: Path, status: int | None, retryable: bool) -> None:
    class Response:
        status_code = status

    class Failing:
        def search(self, params: dict[str, Any]) -> dict[str, Any]:
            error = TimeoutError("read timed out")
            if status is not None:
                error.response = Response()  # type: ignore[attr-defined]
            raise error

    client = SearchClient(api_key=KEY, cache_dir=tmp_path)
    client._client = Failing()
    with pytest.raises(SearchError) as e:
        client.search({"engine": "google", "q": "x"})
    assert e.value.retryable is retryable
