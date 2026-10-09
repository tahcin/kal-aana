"""Passport offices: a central government charter, not the Sakala law, and Google listings named like the office."""

from datetime import date

import pytest

from kalaana import ask, views

TODAY = date(2026, 10, 8)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(views, "clock_today", lambda: TODAY)


def test_passport_limits_come_from_the_charter_with_their_terms() -> None:
    data, _ = views.find_office("psk-lalbagh")
    assert views.allows(data["profile"]) == "the Citizen's Charter promises"
    fresh = next(t for t in data["timelines"] if t["id"] == "passport-fresh")
    assert views.terms(fresh, data["profile"]) == "from the receipt of complete documentation, excluding the police verification period"
    rto, _ = views.find_office("rto-ka05")
    assert views.allows(rto["profile"]) == "the law allows"


def test_a_count_that_includes_police_verification_never_claims_a_missed_limit() -> None:
    out = ask.answer("new passport applied 40 days ago jalahalli", TODAY)["answer"]
    assert "can't show whether the limit was missed" in out["headline"] and "past the limit" not in out["headline"]
    letter = views.complaint("psk-lalbagh", "passport-fresh", "2026-08-01")["draft"]
    assert letter["uncertain"] is True and letter["overdue"] is False


def test_reissue_answers_say_which_of_the_two_limits_they_assume() -> None:
    out = ask.answer("applied for passport renewal at Lalbagh PSK 3 weeks ago, still nothing", TODAY)["answer"]
    assert "7 working days" in out["headline"] and any("police verification" in line for line in out["lines"])


def test_complaint_letters_go_to_the_rpo_grievance_address() -> None:
    letter = views.complaint("psk-whitefield", "passport-reissue", "2026-09-10")["draft"]["letter"]
    assert "grievance.rpoblr@mea.gov.in" in letter and "Regarding my application at Passport Seva Kendra, Whitefield" in letter
    assert "Sakala" not in letter


def test_a_helpline_on_a_listing_is_named_as_one() -> None:
    data, o = views.find_office("rpo-bengaluru")
    assert views.maps_status(o) == "helpline"
    assert views.verdict(o, data)[0].startswith("Its Google Maps listing shows a helpline (1800 258 1800)")


def test_lookalikes_are_named_like_the_office_but_are_not_one() -> None:
    data, _ = views.find_office("psk-lalbagh")
    titles = [x["title"].lower() for x in data["lookalikes"]]
    assert titles and all("passport" in t for t in titles)
    assert not any("park" in t for t in titles)  # a parking lot is a facility, not a lookalike
    assert all(set(x) == {"title", "category", "pincode", "reviews", "lat", "lng"} for x in data["lookalikes"])  # no phone numbers


def test_tatkal_is_not_read_as_stuck_and_helpline_answers_are_named() -> None:
    assert ask.find_intent("tatkal passport whitefield psk phone number") == "reach"
    data, o = views.find_office("psk-whitefield")
    assert any(line.startswith("Google's AI Overview leads with a helpline (1800 258 1800)") for line in views.verdict(o, data))
