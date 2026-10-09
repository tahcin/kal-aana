"""The MCP tools, called through the server the way an assistant would call them."""

import asyncio
from pathlib import Path
import json
import sys
from typing import Any

import pytest

pytest.importorskip("mcp", reason='the MCP server is an optional extra: pip install -e ".[mcp]"')
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from kalaana import mcp_server, snapshot  # noqa: E402


def call(tool: str, **arguments: Any) -> Any:
    result = asyncio.run(mcp_server.server.call_tool(tool, arguments))
    return result.structured_content or json.loads(result.content[0].text)


def test_tools_are_listed_and_read_only() -> None:
    tools = {t.name: t for t in asyncio.run(mcp_server.server.list_tools())}
    assert set(tools) == {"how_to_reach", "office_report", "compare_offices", "statutory_timeline", "read_a_complaint",
                          "check_wait", "google_ai_answers", "office_reviews", "draft_complaint", "search_official_sites",
                          "search_news", "best_time_to_visit"}
    assert all(t.annotations and t.annotations.read_only_hint for t in tools.values())
    # Only the live searches reach the open web (and spend a credit).
    assert {n for n, t in tools.items() if t.annotations.open_world_hint} == {"search_official_sites", "search_news"}


def test_the_chat_tools_answer_from_the_snapshot() -> None:
    wait = mcp_server.check_wait("RTO South", "learners-licence", "2026-09-01")
    assert wait["limit"] == "7 working days" and wait["wait"]["elapsed"] is not None
    assert mcp_server.office_reviews("Varthur sub-registrar")["issues"]
    assert "letter" in mcp_server.draft_complaint("KA-05", "learners-licence", "2026-09-01")
    with pytest.raises(mcp_server.ToolError, match="within the limit"):
        mcp_server.draft_complaint("KA-05", "learners-licence", mcp_server.chat.views.clock_today().isoformat())


def test_live_search_without_a_key_says_so(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SERPAPI_API_KEY", "")
    monkeypatch.setattr(mcp_server.chat.live, "CACHE", tmp_path)
    with pytest.raises(mcp_server.ToolError, match="SerpApi key"):
        mcp_server.search_official_sites("passport fees")


@pytest.mark.parametrize(("query", "code"), [
    ("KA-05", "KA-05"), ("ka 5", "KA-05"), ("KA51", "KA-51"), ("RTO South", "KA-05"), ("Anjanapura RTO", "KA-05"),
    ("560108", "KA-05"), ("Yelahanka RTO", "KA-50"), ("jnanabharathi", "KA-41"), ("KR Puram RTO", "KA-53"),
    ("K.R. Puram RTO", "KA-53"), ("Electronic city rto", "KA-51"), ("Rajajinagar RTO", "KA-02"),
    ("Shanthinagar RTO", "KA-57"), ("HSR Layout RTO", "KA-01"),
])
def test_rtos_are_found_by_code_name_or_address(query: str, code: str) -> None:
    assert mcp_server.find_office(query)["code"] == code


@pytest.mark.parametrize(("query", "office_id"), [
    ("Basavanagudi sub-registrar", "sro-basavanagudi"), ("sub registrar office Varthur", "sro-varthuru"),
    ("Malleswaram SRO", "sro-malleshwaram"), ("Yelahanka sub registrar", "sro-yelahanka"),
    ("J P Nagar sub registrar", "sro-jp-nagara"), ("JP Nagar SRO", "sro-jp-nagara"),
])
def test_sub_registrar_offices_are_found_by_name(query: str, office_id: str) -> None:
    assert mcp_server.find_office(query)["id"] == office_id


@pytest.mark.parametrize("query", ["Yelahanka", "Rajajinagar", "KR Puram"])
def test_a_place_with_both_kinds_of_office_asks_which(query: str) -> None:
    with pytest.raises(ToolError, match="Say 'RTO' or 'sub-registrar'"):
        mcp_server.find_office(query)


@pytest.mark.parametrize("query", ["Jayanagar RTO", "Koramangala RTO", "Bengaluru RTO", "RTO near me", "office", "KA 500", "Chikka 3", ""])
def test_never_guesses_a_wrong_office(query: str) -> None:
    # A wrong office means a wrong phone number: unclear queries must ask, not guess.
    with pytest.raises(ToolError, match="KA-05|could be any of"):
        mcp_server.find_office(query)


def test_errors_reach_the_model_over_stdio() -> None:
    """Over the protocol a ToolError arrives as an error result the model can read, with the known offices."""
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    async def ask() -> Any:
        params = StdioServerParameters(command=sys.executable, args=["-m", "kalaana.mcp_server"])
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            return await session.call_tool("how_to_reach", {"office": "Koramangala RTO"})

    result = asyncio.run(asyncio.wait_for(ask(), 60))
    assert result.is_error and "KA-05" in result.content[0].text and "neighbourhood" in result.content[0].text


@pytest.mark.parametrize("code", [o["code"] for o in snapshot.load("Bengaluru", "rto")["offices"]])
def test_every_office_answers(code: str) -> None:
    reach, report = call("how_to_reach", office=code), call("office_report", office=code)
    assert reach["office"].startswith(code) and report["caveats"] and reach["caveats"]


def test_how_to_reach_gives_official_contacts_and_what_google_shows() -> None:
    answer = call("how_to_reach", office="RTO South")
    assert answer["official_contacts"]["phones"][0]["display"] == "080 2663 0989"
    assert answer["what_google_shows"]["maps_listing"]["phone"] is None
    assert all(len(q["review_text"]) <= mcp_server.QUOTE_CHARS + 1 for q in answer["reviewers_on_phones"])


def test_compare_offices_explains_its_score() -> None:
    answer = call("compare_offices")
    scores = [o["listing_score"] for o in answer["offices"] if o["listing_score"] is not None]
    assert scores == sorted(scores) and answer["offices"][-1]["listing_score"] is None
    assert "not the quality" in answer["listing_score_explained"]
    sros = call("compare_offices", office_type="subregistrar")["offices"]
    assert len(sros) == 43 and {o["recent_reviews_reporting_a_problem"] for o in sros} >= {"not sampled"}


def test_statutory_timeline() -> None:
    names = {m["service"]: m["time_limit"] for m in call("statutory_timeline", service="learner")["matches"]}
    assert names["Issue of learner's licence"] == "7 working days"
    assert [m["service"] for m in call("statutory_timeline", service="driving licence")["matches"]] == [
        "Issue of driving licence", "Duplicate driving licence", "International driving permit", "Renewal of driving licence",
        "Add a vehicle class to a driving licence"]
    assert {m["office_type"] for m in call("statutory_timeline", service="encumbrance certificate")["matches"]} == {"Sub-Registrar Office"}
    assert {m["office_type"] for m in call("statutory_timeline", service="marriage certificate")["matches"]} == {"Sub-Registrar Office"}
    registration = call("statutory_timeline", service="immovable property")["matches"]
    assert [(m["time_limit"], m["office_type"]) for m in registration] == [("1 working day", "Sub-Registrar Office")]
    with pytest.raises(ToolError, match="Services covered"):
        asyncio.run(mcp_server.server.call_tool("statutory_timeline", {"service": "fishing permit"}))


def test_unsampled_offices_report_nothing_rather_than_zero() -> None:
    report = call("office_report", office="BDA sub-registrar")
    assert report["recent_reviews"]["sampled"] is False and "reporting_a_problem" not in report["recent_reviews"]
    assert "isn't proof none exists" in call("how_to_reach", office="BDA sub-registrar")["phone_check"]
    assert "no reviews to read" in call("office_report", office="BDA sub-registrar")["recent_reviews"]["note"]
    row = next(o for o in call("compare_offices", office_type="subregistrar")["offices"] if "BDA" in o["office"])
    assert row["possible_breaches"] is None and row["recent_reviews_reporting_a_problem"] == "not sampled"


def test_read_a_complaint_answers_from_the_evidence() -> None:
    out = mcp_server.read_a_complaint("applied for an EC at Basavanagudi on 12 Sep, still nothing")
    assert out["understood"]["office"]["id"] == "sro-basavanagudi" and out["understood"]["service"] == "encumbrance-certificate"
    assert "working days" in out["answer"]["headline"]


def test_a_search_the_saved_data_answers_points_to_mcp_tools() -> None:
    with pytest.raises(mcp_server.ToolError) as e:
        mcp_server.search_official_sites("RTO South phone number")
    assert "how_to_reach" in str(e.value) and "find_office" not in str(e.value)


def test_the_hosted_server_rations_live_searches_and_model_reads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(mcp_server.chat.live, "CACHE", tmp_path)
    monkeypatch.setattr(mcp_server, "_recent", {"live": mcp_server.deque(), "read": mcp_server.deque()})
    monkeypatch.setattr(mcp_server, "LIVE_PER_HOUR", 0)
    with pytest.raises(mcp_server.ToolError, match="used up for the hour"):
        mcp_server.search_official_sites("passport fees")
    monkeypatch.setattr(mcp_server, "READS_PER_HOUR", 0)
    monkeypatch.setattr(mcp_server.reader, "configured", lambda: "anthropic")
    with pytest.raises(mcp_server.ToolError, match="for the hour"):
        mcp_server.read_a_complaint("my learner's licence from RTO South is 3 weeks late")
