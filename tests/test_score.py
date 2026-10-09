"""Scoring rules. The listings and reviews here are hand-made test fixtures shaped like a saved
collection; the official offices and timelines are the real ones from data/official.
"""

from datetime import date
from typing import Any

import pytest

from kalaana import official, taxonomy
from kalaana.collect import NEWEST
from kalaana.score import (
    GOV_SITE, MIN_SAMPLE, OfficeScore, possible_breach, reported_days, score_collection, score_office, service_named,
    went_through_agent,
)

AS_OF = date(2026, 10, 8)
DATA = official.load()
KA05 = DATA.offices["rto-ka05"]
RTO_TIMELINES = {t.id: t for t in DATA.timelines_for("rto")}


def review(rid: str, text: str, when: str = "2026-09-01", rating: float = 1.0, samples: tuple[str, ...] = (NEWEST,)) -> dict[str, Any]:
    return {"review_id": rid, "data_id": "0xka05", "rating": rating, "iso_date": f"{when}T10:00:00Z", "text": text,
            "text_original": "", "likes": 0, "link": f"https://maps.example/{rid}", "samples": list(samples)}


def listing(**extra: Any) -> dict[str, Any]:
    return {"data_id": "0xka05", "title": "Regional Transport Office (KA 05)", "phone_raw": "", "website": "",
            "has_hours": True, "unclaimed": True, "reviews": 240, **extra}


def evidence(reviews: list[dict[str, Any]], **listing_extra: Any) -> dict[str, Any]:
    return {"primary_id": "0xka05", "listings": [listing(**listing_extra)], "reviews": reviews}


def scored(reviews: list[dict[str, Any]], **listing_extra: Any) -> OfficeScore:
    return score_office(KA05, evidence(reviews, **listing_extra), DATA, "Bengaluru", AS_OF)


def check(score: OfficeScore, check_id: str) -> Any:
    return next(c for c in score.reachability.checks if c.id == check_id)


# Durations and services


@pytest.mark.parametrize(("sentence", "expected"), [
    ("LL test has been completed, 20days also over", (20, "20days")),
    ("I submitted it almost 3 months ago", (90, "almost 3 months")),
    ("still pending after more than a month", (30, "more than a month")),
    ("work will take atleast 1.5months", None),  # a forecast, not a wait
    ("they promised 60 days; I'm waiting", None),
    ("you will get it within 7 days", None),
    ("no number here", None),
])
def test_reported_days(sentence: str, expected: tuple[int, str] | None) -> None:
    assert reported_days(sentence) == expected


@pytest.mark.parametrize(("sentence", "review_text", "service"), [
    ("still LL is not approved", "", "learners-licence"),
    ("I'll wait, they'll say come after 30 days", "", None),  # "I'll" is not LL
    ("My DL renewal application was stuck for nearly 4 weeks", "", "licence-renewal"),
    ("I wanted to get my DL renewed, pending 40 days", "", "licence-renewal"),
    ("it has been 2 months", "I applied for my RC transfer. It has been 2 months", "transfer-of-ownership"),
    ("it has been 2 months", "Applied for LL and DL together. It has been 2 months", None),  # two services: no guess
    ("hypothecation termination pending almost 3 months", "", None),  # not a Sakala-notified service
    ("to get my NOC Cancelled, more than 60 days", "", None),
    ("3 months later have not received my vehicle registration card", "", None),  # a card in the post
    ("DL renewal and address change pending four weeks", "", None),  # no timeline for the combined service
])
def test_service_named(sentence: str, review_text: str, service: str | None) -> None:
    found = service_named(sentence, review_text or sentence, RTO_TIMELINES)
    assert (found.id if found else None) == service


def test_possible_breach_shows_its_arithmetic_in_the_reviewers_words() -> None:
    r = review("r1", "Worst RTO office, LL test has been completed, 20days also over, still LL is not approved.")
    breach = possible_breach(r, taxonomy.classify(r["text"])["delay"], RTO_TIMELINES, frozenset())
    assert breach and (breach.reported_days, breach.reported_working_days, breach.service.days) == (20, 14, 7)
    assert '"20days"' in breach.explanation and "7 working days" in breach.explanation


@pytest.mark.parametrize("text", [
    "My LL is still not approved, it has been 8 days.",  # within the timeline
    "My DL took about a month to come.",  # 21 working days against 20: too close to call
])
def test_no_breach_within_or_near_the_timeline(text: str) -> None:
    r = review("r1", text)
    assert possible_breach(r, taxonomy.classify(r["text"])["delay"], RTO_TIMELINES, frozenset()) is None


@pytest.mark.parametrize(("text", "used"), [
    ("I applied through an agent and paid him 2000, it has been 1 month", True),
    ("They introduced me to some agent, he asked me to pay 2500", True),
    ("The agent told me the inspector wants more", True),
    ("If I had gone through an agent it would be done", True),  # conservative: set aside
    ("Agents everywhere but I did it myself", False),
])
def test_went_through_agent(text: str, used: bool) -> None:
    assert went_through_agent(text) is used


def test_breaches_are_recent_and_agent_waits_set_aside() -> None:
    s = scored([
        review("own", "LL test done, 20 days over, still LL is not approved.", "2026-07-07"),
        review("agent", "I applied through an agent for my LL, 30 days over, still LL is not approved.", "2026-06-01"),
        review("old", "LL test done, 20 days over, still LL is not approved.", "2018-10-20"),
    ])
    assert [b.quote.review_id for b in s.breaches] == ["own"]
    assert [b.quote.review_id for b in s.agent_waits] == ["agent"]
    assert s.older_breaches == 1


# Reachability


def test_reachability_of_an_office_with_no_phone() -> None:
    s = scored([])
    assert check(s, "phone").passed is False and check(s, "own_number").passed is None  # no double penalty
    assert check(s, "hours").passed is True and check(s, "claimed").passed is False
    assert check(s, "gets_through").passed is None
    assert s.reachability.score == round(100 * 10 / 55) and s.reachability.basis == "4 of 6 checks"


@pytest.mark.parametrize(("phone", "passed", "detail"), [
    ("080 2663 0989", True, "official directory"),
    ("0120 492 5505", False, "national queue"),
    ("0816 227 8473", False, "STD code of Tumkur"),
    ("98450 00000", False, "not in the official directory"),
])
def test_the_number_shown_is_checked_against_the_directory(phone: str, passed: bool, detail: str) -> None:
    s = scored([], phone_raw=phone)
    assert check(s, "phone").passed and check(s, "own_number").passed is passed and detail in check(s, "own_number").detail


def test_gets_through() -> None:
    talk = [review(f"t{i}", "I tried to call them about my LL", samples=("query:phone",)) for i in range(3)]
    fail = review("f", "The phone number is out of order", "2026-07-07", samples=("query:phone",))
    assert check(scored(talk + [fail]), "gets_through").passed is False
    assert check(scored([fail]), "gets_through").passed is False  # one recent report is enough to fail
    old = dict(fail, iso_date="2019-01-01T10:00:00Z")
    passed = check(scored(talk + [old]), "gets_through")
    assert passed.passed is True and "older than that do" in passed.detail
    assert check(scored(talk[:2]), "gets_through").passed is None  # too few to pass
    agent = review("a", "The agent took my money and doesn't even take my phone calls", "2026-07-07", samples=("query:phone",))
    assert check(scored(talk + [agent]), "gets_through").passed is True  # an agent's phone, not the office's
    numbers = [review(f"n{i}", "Note your application number and RC number") for i in range(5)]
    assert check(scored(numbers), "gets_through").passed is None  # application numbers aren't phones


@pytest.mark.parametrize(("url", "is_gov"), [
    ("https://transport.karnataka.gov.in/x", True), ("http://sakala.kar.nic.in", True),
    ("https://parivahan.gov.in:8080/?q=1", True), ("https://rto-helper.example.com", False), ("https://gov.in.example.com", False),
])
def test_government_websites(url: str, is_gov: bool) -> None:
    assert bool(GOV_SITE.search(url)) is is_gov


def test_office_without_a_listing_is_not_scored() -> None:
    s = score_office(DATA.offices["rto-ka59"], {"primary_id": "", "listings": [], "reviews": []}, DATA, "Bengaluru", AS_OF)
    assert s.reachability.score is None and s.listing is None and s.problem_share is None


# Issue counts


def test_counts_come_from_the_last_year_of_the_newest_sample_only() -> None:
    window = [review(f"n{i}", "Very helpful staff", rating=5) for i in range(MIN_SAMPLE - 2)]
    window += [review("b1", "Pay a bribe or wait"), review("b2", "Bribe at every table"), review("s", "", rating=3)]
    old = [review("o1", "bribe bribe", "2023-01-01")]  # in the sample, outside the window
    evidence_only = [review(f"q{i}", "bribe bribe bribe", samples=("query:bribe",)) for i in range(20)]
    s = scored(window + old + evidence_only)
    bribe = next(i for i in s.issues if i.category == "bribe")
    assert (s.sample_size, s.window_reviews, bribe.count, bribe.of) == (MIN_SAMPLE + 2, MIN_SAMPLE, 2, MIN_SAMPLE)
    assert s.problem_share == pytest.approx(0.2) and s.positive_share == pytest.approx(0.8)
    assert [q.sample for q in bribe.quotes][:2] == [NEWEST, NEWEST]  # counted reviews are quoted first
    assert s.span == ("2023-01-01", "2026-09-01")
    small = scored(window[:5])
    assert not small.enough_evidence and small.problem_share is None


def test_quotes_are_masked() -> None:
    s = scored([review("n1", "Agent named Farhan took a bribe, call 9845012345")])
    quote = next(i for i in s.issues if i.category == "bribe").quotes[0]
    assert "Farhan" not in quote.text and "9845012345" not in quote.text and "[name]" in quote.text


def test_sarcastic_praise_in_a_one_star_review_is_not_counted() -> None:
    s = scored([review("n1", "Very efficient office indeed", rating=1)])
    assert next(i for i in s.issues if i.category == "helpful").count == 0


def test_undated_and_malformed_reviews_dont_crash() -> None:
    weird = [dict(review("u1", "bribe here"), iso_date=None), dict(review("u2", "delay of 3 months for LL"), samples=[])]
    s = scored(weird)
    assert s.window_reviews == 0 and s.span is None


def test_score_collection_uses_the_collection_date() -> None:
    collection = {"collected_at": "2026-10-08T12:00:00+0530", "city": "Bengaluru",
                  "offices": {"rto-ka05": evidence([review("n1", "Very helpful staff", "2025-11-01", 5)])}}
    [s] = score_collection(collection, DATA)
    assert s.window_reviews == 1  # inside the year before Oct 8, 2026
