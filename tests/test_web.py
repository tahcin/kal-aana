"""The web app's JSON API and the built React app: complete, correct, and nothing private leaks through it."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from kalaana import views, web
from test_snapshot import _official_mobiles, full_mobiles

client = TestClient(web.app)
OFFICE_IDS = [o["id"] for _, o in views.everything()]


def test_overview_covers_every_office() -> None:
    data = client.get("/api/overview").json()
    assert len(data["offices"]) == len(data["points"]) == len(OFFICE_IDS) == 60
    assert data["totals"]["searches"] == sum(t["searches"] for t in data["types"].values())
    assert data["totals"]["searches"] == sum(n for t in data["types"].values() for n in t["searches_by_engine"].values())
    assert not full_mobiles(client.get("/api/overview").text) - _official_mobiles()


@pytest.mark.parametrize("office_id", OFFICE_IDS)
def test_every_office_publishes_no_private_mobile(office_id: str) -> None:
    for path in (f"/api/office/{office_id}", f"/api/story/{office_id}", f"/api/office/{office_id}/complaint"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert not full_mobiles(response.text) - _official_mobiles(), path
        assert '"phone_raw"' not in response.text


def test_unknown_things_are_404() -> None:
    assert client.get("/api/office/nope").status_code == 404
    assert client.get("/api/story/nope").status_code == 404
    assert client.get("/api/snapshot?office_type=police").status_code == 404
    assert client.get("/api/nothing-here").status_code == 404


def test_snapshot_api_carries_no_reviewer_identity() -> None:
    page = client.get("/api/snapshot?office_type=rto").text
    assert '"user"' not in page and "contrib" not in page


@pytest.mark.skipif(not (web.BUILD / "index.html").exists(), reason="the app isn't built")
@pytest.mark.parametrize("path", ["/", "/map", "/offices", "/office/rto-ka05", "/method"])
def test_the_app_serves_every_route(path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200 and '<div id="root">' in response.text


def test_unknown_api_paths_are_json_404s() -> None:
    for path in ("/api", "/api/", "/api/nothing/here"):
        response = client.get(path)
        assert response.status_code == 404 and response.headers["content-type"].startswith("application/json"), path


def test_missing_files_are_404_not_the_app() -> None:
    for path in ("/assets/missing.js", "/favicon.ico", "/robots.txt", "/assets/missing.css"):
        response = client.get(path)
        assert response.status_code == 404 and '<div id="root">' not in response.text, path


@pytest.mark.skipif(not (web.BUILD / "index.html").exists(), reason="the app isn't built")
def test_head_requests_work_for_routes_and_files() -> None:
    assert client.head("/map").status_code == 200
    assert client.head("/").status_code == 200
    assert client.head("/api/nothing").status_code == 404
    asset = next((web.BUILD / "assets").glob("*.js"))
    assert client.head(f"/assets/{asset.name}").status_code == 200


def test_the_app_never_serves_files_outside_its_build() -> None:
    assert "kal-aana" not in client.get("/..%2F..%2Fpyproject.toml").text


def test_working_days_skip_sundays_and_second_and_fourth_saturdays() -> None:
    # Oct 2-12, 2026: Sat 3 is the 1st Saturday (working); Sun 4, Sat 10 (2nd) and Sun 11 are off.
    # Oct 2 is a public holiday but counts: public holidays aren't skipped, so this is an upper bound.
    assert views.working_days_since(date(2026, 10, 1), date(2026, 10, 12)) == 8


def test_complaint_letter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(views, "clock_today", lambda: date(2026, 10, 8))
    out = client.get("/api/office/rto-ka05/complaint?service=learners-licence&applied=2026-06-10&number=LL%2F123").json()
    d = out["draft"]
    assert d["overdue"] and d["limit"] == "7 working days" and "LL/123" in d["letter"]
    assert "Karnataka Sakala Services Act, 2011" in d["letter"] and "The Regional Transport Officer" in d["letter"]
    assert "Joint Commissioner for Transport" in d["letter"] and out["problem"] is None
    assert client.get("/api/office/rto-ka05/complaint").json()["draft"] is None
    bad = client.get("/api/office/rto-ka05/complaint?service=learners-licence&applied=not-a-date").json()
    assert bad["problem"] and bad["draft"]["applied"] is None
    future = client.get("/api/office/rto-ka05/complaint?service=learners-licence&applied=2030-01-01").json()
    assert "future" in future["problem"] and "Status of my application" in future["draft"]["letter"]


def test_complaint_to_a_sub_registrar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(views, "clock_today", lambda: date(2026, 10, 8))
    d = client.get("/api/office/sro-varthuru/complaint?service=property-registration&applied=2026-10-01").json()["draft"]
    assert "The Sub-Registrar" in d["letter"] and "1 working day" in d["letter"] and "Regional Transport" not in d["letter"]


def test_complaint_number_cannot_inject_lines() -> None:
    d = client.get("/api/office/rto-ka05/complaint?service=learners-licence&number=A%0ASubject:%20x").json()["draft"]
    assert "\nSubject: x" not in d["letter"]


def test_map_has_every_office_and_the_shared_number() -> None:
    points = views.map_points()
    assert len(points) == len(OFFICE_IDS)
    assert sum(p["status"] == "no_listing" for p in points) == sum(p["lat"] is None for p in points)
    assert [sorted(l["ids"]) for l in views.shared_links()] == [["sro-jp-nagara", "sro-varthuru"]]


def test_story_checks_the_ai_address_and_flags_the_shared_number() -> None:
    ka05 = client.get("/api/story/rto-ka05").json()
    assert ka05["ai"]["address_matches"] is False and ka05["clock"]["limit"] == "7 working days"
    assert ka05["clock"]["reported_days"] and "20days" in ka05["clock"]["said"] and "five working days" in ka05["clock"]["conversion"]
    assert any(m.startswith("+91-80") for m in ka05["ai"]["good_marks"])
    varthur = client.get("/api/story/sro-varthuru").json()
    assert any("JP Nagara" in f.get("also", "") for f in varthur["found"])
    assert client.get("/api/story/sro-halasooru").json()["checked"] is False  # its Google search never ran
    assert client.get("/api/story/sro-bda").json()["sampled"] is False  # no listing, so no reviews to read


def test_story_takeaways_are_one_plain_sentence_per_step() -> None:
    ka05 = client.get("/api/story/rto-ka05").json()["takeaways"]
    assert ka05["search"] == ("So a citizen who searches gets the right number, but an address with a different PIN from the directory's. "
                              "Google's AI Mode, asked the same thing, leads with the office's own number and PIN.")
    assert ka05["maps"] == "So the office's own Google listing, with 240 reviews, shows no phone number. Bing Maps shows no phone either."
    assert ka05["check"] == "So the one number Google showed up front is the office's own. The department publishes 4."
    assert ka05["clock"] == "So one reviewer reports waiting about 14 working days for a learner's licence, which the law promises in 7 working days."
    # Official numbers that only other websites list, further down the results, are counted too.
    assert "other websites list 3 of the department's numbers" in client.get("/api/story/rto-ka51").json()["takeaways"]["check"]
    assert "another office's listing shows the same one" in client.get("/api/story/sro-varthuru").json()["takeaways"]["maps"]
    bda = client.get("/api/story/sro-bda").json()["takeaways"]
    assert bda["check"] == "So none of the 3 numbers Google showed up front is the office's own. The department publishes 1."
    assert client.get("/api/story/sro-halasooru").json()["takeaways"]["search"] == "So the rest of this office's story comes from Google Maps alone."
    for office_id in OFFICE_IDS:
        lines = client.get(f"/api/story/{office_id}").json()["takeaways"].values()
        assert all(line.startswith("So ") and line.endswith(".") and "—" not in line for line in lines)
        assert not any("of the 1 number" in line or "the 1 number" in line or "anything Google" in line for line in lines)

    searches = [s["search_id"] for s in client.get(f"/api/story/{office_id}").json()["searches"]]
    assert len(searches) == len(set(searches))


def test_story_names_the_serpapi_search_behind_each_step() -> None:
    ka05 = client.get("/api/story/rto-ka05").json()
    engines = [s["engine"] for s in ka05["searches"]]
    assert engines[0] == "google_maps" and ka05["searches"][0]["search_id"] == ka05["maps"]["search_id"]
    assert {"google", "google_ai_overview", "google_maps_reviews"} <= set(engines)
    assert ka05["ai"]["overview_search_id"] in {s["search_id"] for s in ka05["searches"] if s["engine"] == "google_ai_overview"}
    assert ka05["clock"]["search_id"] in {s["search_id"] for s in ka05["searches"] if s["engine"] == "google_maps_reviews"}
    assert "cars24.com" in [src["domain"] for src in ka05["ai"]["sources"]]


def test_clock_note_is_honest_about_older_and_agent_waits() -> None:
    assert client.get("/api/story/rto-ka01").json()["clock"]["note"].endswith("Older reviews do.")
    assert "apart from waits through an agent" in client.get("/api/story/rto-ka53").json()["clock"]["note"]
    assert "weren't sampled" in client.get("/api/story/sro-bda").json()["clock"]["note"]


def test_verdict_sentences_come_from_the_data() -> None:
    data, office = views.find_office("rto-ka05")
    lines = views.verdict(office, data)
    assert lines[0].startswith("Its Google Maps listing shows no phone number") and "unclaimed" in lines[0]
    assert "different PIN" in lines[1] and '"20days also over"' in lines[2]


def test_the_visitor_is_cloudflares_address_only_behind_the_tunnel(monkeypatch: pytest.MonkeyPatch) -> None:
    request = type("R", (), {"headers": {"cf-connecting-ip": "203.0.113.7"}, "client": type("C", (), {"host": "127.0.0.1"})()})()
    monkeypatch.setattr(web, "PROXY", "")
    assert web._visitor(request) == "127.0.0.1"  # a header anyone can send is ignored unless the tunnel is configured
    monkeypatch.setattr(web, "PROXY", "cloudflare")
    assert web._visitor(request) == "203.0.113.7"


def test_the_daily_question_cap_holds_across_visitors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(web.reader, "configured", lambda: "anthropic")
    monkeypatch.setattr(web, "DAILY_QUESTIONS", 2)
    monkeypatch.setattr(web, "PROXY", "cloudflare")
    monkeypatch.setattr(web, "_today", {})
    monkeypatch.setattr(web, "_asked", web.defaultdict(web.deque))
    for ip in ("198.51.100.1", "198.51.100.2"):
        web._limit(type("R", (), {"headers": {"cf-connecting-ip": ip}, "client": None})())
    with pytest.raises(web.HTTPException) as e:
        web._limit(type("R", (), {"headers": {"cf-connecting-ip": "198.51.100.3"}, "client": None})())
    assert e.value.status_code == 429


def test_cors_is_off_unless_origins_are_listed() -> None:
    response = client.get("/api/overview", headers={"Origin": "https://elsewhere.example"})
    assert "access-control-allow-origin" not in response.headers
