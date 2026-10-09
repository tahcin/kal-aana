"""Live searches: rationing, the official-site filter and masking, against a fake SerpApi (no credits spent)."""

from pathlib import Path
from typing import Any

import pytest

from kalaana import live


class FakeSerpApi:
    def __init__(self, left: int = 600):
        self.left, self.searches = left, []

    def account(self) -> dict[str, Any]:
        return {"total_searches_left": self.left}

    def search(self, params: dict[str, Any]) -> dict[str, Any]:
        self.searches.append(params)
        if params["engine"] == "google_news":
            return {"search_metadata": {"id": "news1"}, "news_results": [
                {"title": "Sarathi portal glitch", "link": "https://example.com/a", "source": {"name": "Paper"}, "iso_date": "2026-06-17T07:00:00Z"}]}
        return {"search_metadata": {"id": "web1"}, "organic_results": [
            {"title": "LL procedure", "link": "https://transport.karnataka.gov.in/ll", "snippet": "Call 9845012345 or 080 2663 0989."},
            {"title": "A blog", "link": "https://www.scribd.com/doc", "snippet": "Some advice"},
            {"title": "Old page", "link": "http://insecure.gov.in/x", "snippet": "no https"}]}


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeSerpApi:
    serp = FakeSerpApi()
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    monkeypatch.setenv("KALAANA_LIVE_TOTAL", "300")
    monkeypatch.setattr(live, "LEDGER", tmp_path / "live.json")
    monkeypatch.setattr(live, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(live, "_account", {"at": 0.0, "left": None})
    monkeypatch.setattr(live.SearchClient, "_serpapi", lambda self: serp)
    return serp


def test_official_only_keeps_government_https_pages_and_masks_unlisted_mobiles(fake: FakeSerpApi) -> None:
    found = live.search_web("learner licence documents", official_only=True)
    assert fake.searches[0]["as_sitesearch"] == "gov.in"
    assert [r["domain"] for r in found["results"]] == ["transport.karnataka.gov.in"] and not found["no_official"]
    snippet = found["results"][0]["snippet"]
    assert "9845012345" not in snippet and "98••• •••45" in snippet and "080 2663 0989" in snippet


def test_other_sites_are_marked_not_official(fake: FakeSerpApi) -> None:
    found = live.search_web("learner licence documents", official_only=False)
    assert [(r["domain"], r["official"]) for r in found["results"]] == [("transport.karnataka.gov.in", True), ("scribd.com", False)]


def test_a_repeat_within_the_hour_is_free(fake: FakeSerpApi) -> None:
    live.search_web("passport fees")
    again = live.search_web("passport fees")
    assert len(fake.searches) == 1 and not again["fresh"] and live.ledger()["total"] == 1


def test_the_daily_and_total_limits_stop_live_search(fake: FakeSerpApi, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KALAANA_LIVE_DAILY", "2")
    live.search_web("a")
    live.search_news("b")
    with pytest.raises(live.LiveUnavailable, match="allowance"):
        live.search_web("c")
    monkeypatch.setenv("KALAANA_LIVE_DAILY", "40")
    monkeypatch.setenv("KALAANA_LIVE_TOTAL", "2")
    with pytest.raises(live.LiveUnavailable, match="allowance"):
        live.search_web("d")
    assert len(fake.searches) == 2


def test_the_credit_reserve_is_never_touched(fake: FakeSerpApi) -> None:
    fake.left = 250
    with pytest.raises(live.LiveUnavailable, match="reserve"):
        live.search_web("passport fees")
    assert not fake.searches


def test_a_damaged_ledger_counts_as_spent(fake: FakeSerpApi) -> None:
    live.LEDGER.write_text("{not json")
    with pytest.raises(live.LiveUnavailable, match="allowance"):
        live.search_web("passport fees")


def test_news_results_carry_their_dates(fake: FakeSerpApi) -> None:
    found = live.search_news("Sarathi down")
    assert found["results"][0]["date"].startswith("2026-06-17") and found["results"][0]["source"] == "Paper"


def test_with_no_government_page_the_others_are_kept_but_marked(fake: FakeSerpApi, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(FakeSerpApi, "search", lambda self, params: {"search_metadata": {"id": "w"}, "organic_results": [
        {"title": "Form 29", "link": "https://www.scribd.com/form29", "snippet": "a scan"}]})
    found = live.search_web("form 29", official_only=True)
    assert found["no_official"] and [(r["domain"], r["official"]) for r in found["results"]] == [("scribd.com", False)]


@pytest.mark.parametrize("link", ["https://evil.com?.gov.in", "https://evil.com#.nic.in", "https://evil.com\\@a.gov.in/",
                                  "https://evil.com:443?x=.gov.in", "https://gov.in@evil.com", "https://gov.in.evil.com/x",
                                  "https://evilgov.in", "http://transport.karnataka.gov.in", "https://xn--gov-in.com",
                                  "https://a.gov.in:8443/x", "https://a gov.in"])
def test_no_disguised_or_insecure_link_counts_as_official(link: str) -> None:
    assert not live.is_official(live.host(link))


@pytest.mark.parametrize("link", ["https://transport.karnataka.gov.in/x", "https://www.passportindia.gov.in/",
                                  "https://sakala.kar.nic.in", "https://a.gov.in./"])
def test_government_hosts_count_as_official(link: str) -> None:
    assert live.is_official(live.host(link))


def test_another_site_cannot_put_a_number_in_front_of_a_citizen(fake: FakeSerpApi, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(FakeSerpApi, "search", lambda self, params: {"search_metadata": {"id": "w"}, "organic_results": [
        {"title": "RTO helpline 1800 123 4567", "link": "https://agent.example.com/x", "snippet": "Call 080-12345678 for fast LL"}]})
    found = live.search_web("rto helpline", official_only=False)
    text = found["results"][0]["title"] + found["results"][0]["snippet"]
    assert "1234567" not in text and "12345678" not in text and "[number]" in text


def test_cached_searches_are_forgotten_after_an_hour(fake: FakeSerpApi) -> None:
    import os, time
    live.search_web("passport fees")
    cached = next(live.CACHE.glob("*.json"))
    os.utime(cached, (time.time() - 4000, time.time() - 4000))
    live.search_web("another question")
    assert not cached.exists()
