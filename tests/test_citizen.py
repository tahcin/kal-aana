"""What Google tells a citizen. Responses are hand-made fixtures shaped like SerpApi's JSON."""

from pathlib import Path
from typing import Any

from kalaana import official
from kalaana.citizen import ai_mode_params, citizen_view, search_name, search_params
from kalaana.client import SearchClient
from kalaana.offices import CITIES

DATA = official.load()
KA05 = DATA.offices["rto-ka05"]
CITY = CITIES["Bengaluru"]


class Fake:
    def __init__(self, responses: dict[str, dict[str, Any]]):
        self.responses = responses

    def search(self, params: dict[str, Any]) -> dict[str, Any]:
        if params["engine"] == "google_ai_mode":
            return self.responses.get("AI Mode", {})
        return self.responses[params.get("q") or params["page_token"]]


def view_for(responses: dict[str, dict[str, Any]], tmp_path: Path) -> Any:
    client = SearchClient(api_key="k" * 64, cache_dir=tmp_path)
    client._client = Fake(responses)
    return citizen_view(client, KA05, DATA, CITY)


def test_query_is_what_a_citizen_types() -> None:
    assert search_name(KA05) == "RTO Bengaluru South"
    assert search_params(KA05, CITY)["q"] == "RTO Bengaluru South phone number"


def test_numbers_and_address_are_checked_against_the_directory(tmp_path: Path) -> None:
    view = view_for({
        "RTO Bengaluru South phone number": {
            "ai_overview": {"page_token": "tok"},
            "local_results": {"places": [{"title": "RTO North", "phone": "080 2337 6039"}]},
            "organic_results": [{"title": "RTO list", "snippet": "Call 0120 492 5505 or 98450 00000", "link": "https://www.example.com/x"}],
        },
        "tok": {"ai_overview": {"text_blocks": [
            {"type": "paragraph", "snippet": "The phone number is +91-80-26630989."},
            {"type": "list", "list": [{"snippet": "Address: Jayanagar, Bengaluru, Karnataka 560011"}]},
        ], "references": [{"title": "Cars24", "link": "https://www.cars24.com/x"}]}},
    }, tmp_path)
    verdicts = {(n.surface, n.phone.display): n.verdict for n in view.numbers}
    assert verdicts == {
        ("ai_overview", "080 2663 0989"): "this office",
        ("local_pack", "080 2337 6039"): "another office",
        ("snippet", "0120 492 5505"): "national helpline",
        ("snippet", "98450 00000"): "not in the directory",
    }
    assert view.ai_pincodes == ["560011"] and view.ai_address_matches(KA05) is False
    assert view.ai_references == [("Cars24", "https://www.cars24.com/x")]


def test_no_ai_overview_and_failed_search(tmp_path: Path) -> None:
    view = view_for({"RTO Bengaluru South phone number": {"organic_results": []}}, tmp_path / "a")
    assert view.ai_text == "" and view.ai_address_matches(KA05) is None
    broken = citizen_view(SearchClient(api_key="", cache_dir=tmp_path / "b"), KA05, DATA, CITY)  # demo mode, nothing cached
    assert broken.notes and not broken.numbers


def test_ai_mode_is_asked_the_same_question_and_checked_the_same_way(tmp_path: Path) -> None:
    assert ai_mode_params(KA05, CITY)["q"] == search_params(KA05, CITY)["q"]
    view = view_for({
        "RTO Bengaluru South phone number": {"ai_overview": {"text_blocks": [{"type": "paragraph", "snippet": "Call 080-26630989, Bengaluru 560011."}]}},
        "AI Mode": {"search_metadata": {"id": "mode1", "created_at": "2026-10-08 07:38:44 UTC"}, "text_blocks": [
            {"type": "list", "list": [{"snippet": "Phone Numbers: 080-26630989, 080-26633853"}, {"snippet": "Address: Anjanapura, Bengaluru - 560108"}]},
        ], "references": [{"title": "Transport Department", "link": "https://transport.karnataka.gov.in/x"}]},
    }, tmp_path)
    assert view.ai_address_matches(KA05) is False and view.mode_address_matches(KA05) is True
    assert [n.phone.display for n in view.numbers if n.surface == "ai_mode"] == ["080 2663 0989", "080 2663 3853"]
    assert all(n.verdict == "this office" for n in view.numbers if n.surface == "ai_mode")
    assert view.mode_search_id == "mode1" and view.mode_searched_on == "2026-10-08"
