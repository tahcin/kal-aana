"""The ask box: free text read into an office, a service, a date and an intent, every field checked."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from kalaana import ask, reader, web

TODAY = date(2026, 10, 8)


@pytest.mark.parametrize(("text", "office", "service", "applied", "intent"), [
    ("Applied for my learner's licence at RTO South 3 weeks ago, still waiting", "rto-ka05", "learners-licence", "2026-09-17", "late"),
    ("My learner's licence from RTO South is 3 weeks late", "rto-ka05", "learners-licence", None, "late"),
    ("KA 05 LL test passed 20 days ago no approval", "rto-ka05", "learners-licence", "2026-09-18", "late"),
    ("phone number for Varthur sub registrar", "sro-varthuru", None, None, "reach"),
    ("applied for EC at Basavanagudi on 12 Sep, still not received", "sro-basavanagudi", "encumbrance-certificate", "2026-09-12", "late"),
    ("driving licence renewal at Yeshwanthpur pending since 01/09/2026", "rto-ka04", "licence-renewal", "2026-09-01", "late"),
    ("agent asked for money at Jayanagar sub-registrar for sale deed", "sro-jayanagara", "property-registration", None, "report"),
])
def test_rules_read_what_people_write(text: str, office: str, service: str | None, applied: str | None, intent: str) -> None:
    got = ask.understand(text, TODAY)
    assert (got["office"] and got["office"]["id"], got["service"], got["applied"], got["intent"]) == (office, service, applied, intent)
    assert got["by"] == "rules"


def test_a_place_with_two_offices_asks_which_and_a_neighbourhood_names_none() -> None:
    both = ask.understand("Yelahanka office number", TODAY)
    assert both["office"] is None and {c["id"] for c in both["candidates"]} == {"rto-ka50", "sro-yelahanka"}
    assert ask.understand("where is the rto in koramangala", TODAY)["office"] is None


def test_dates_are_never_in_the_future_or_before_sakala() -> None:
    assert ask.find_date("applied 12 Dec", TODAY)[0] == date(2025, 12, 12)  # last December, not this one
    assert ask.find_date("applied on 2030-01-01", TODAY)[0] is None
    assert ask.find_date("applied on 2001-01-01", TODAY)[0] is None


def test_answer_counts_working_days_against_the_limit() -> None:
    out = ask.answer("Applied for my learner's licence at RTO South 3 weeks ago, still waiting", TODAY)["answer"]
    assert out["headline"] == ("About 17 working days since you applied (public holidays not subtracted). "
                               "The law allows 7 working days: that's past the limit.")
    assert out["actions"][0]["href"] == "/office/rto-ka05/complaint?service=learners-licence&applied=2026-09-17"
    assert out["official"][0]["display"] == "080 2663 0989"


def test_a_model_reading_is_kept_only_where_it_checks_out(monkeypatch: pytest.MonkeyPatch) -> None:
    invented = reader.Reading(office="RTO Mars", service="teleport-licence", applied="2030-01-01", intent="panic", by="test-model")
    monkeypatch.setattr(reader, "read", lambda *_: invented)
    got = ask.understand("Applied for my learner's licence at RTO South 3 weeks ago, still waiting", TODAY)
    assert got["office"]["id"] == "rto-ka05" and got["service"] == "learners-licence"  # the rules overrule it
    assert got["applied"] == "2026-09-17" and got["intent"] == "late" and got["by"] == "test-model"

    good = reader.Reading(office="KA-05", service="learners-licence", applied="2026-09-01", intent="late", by="test-model")
    monkeypatch.setattr(reader, "read", lambda *_: good)
    got = ask.understand("my LL is stuck, applied on the first of September at south rto", TODAY)
    assert (got["office"]["id"], got["applied"], got["applied_how"]) == ("rto-ka05", "2026-09-01", "the date read from your message")


def test_an_unreachable_model_falls_back_to_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    def down(*_: object) -> None:
        raise reader.ReaderError("Model server unavailable")
    monkeypatch.setattr(reader, "read", down)
    got = ask.understand("phone number for Varthur sub registrar", TODAY)
    assert got["office"]["id"] == "sro-varthuru" and got["by"] == "rules" and "rules read it instead" in got["note"]


def test_the_reader_schema_limits_services_and_intents() -> None:
    s = reader.schema(["learners-licence"])
    assert s["properties"]["service"]["enum"] == ["", "learners-licence"] and s["additionalProperties"] is False


def test_api_ask_answers_and_refuses_overlong_text() -> None:
    client = TestClient(web.app)
    assert client.post("/api/ask", json={"text": "number of RTO Yelahanka"}).json()["understood"]["office"]["id"] == "rto-ka50"
    assert client.post("/api/ask", json={"text": "x" * 500}).status_code == 422


def test_story_follows_the_visitors_own_application(monkeypatch: pytest.MonkeyPatch) -> None:
    from kalaana import views
    monkeypatch.setattr(views, "clock_today", lambda: TODAY)
    client = TestClient(web.app)
    card = client.get("/api/story/sro-basavanagudi?service=encumbrance-certificate&applied=2026-09-12").json()
    assert card["yours"]["elapsed"] == 21 and card["yours"]["overdue"] is True and card["yours"]["limit"] == "5 working days"
    assert card["takeaways"]["clock"] == ("So you've waited about 21 working days on your application (encumbrance certificate); "
                                          "the law allows 5 working days.")
    assert "yours" not in client.get("/api/story/sro-basavanagudi?service=learners-licence").json()  # not this office's service
    assert client.get("/api/story/sro-basavanagudi?service=encumbrance-certificate&applied=2031-01-01").json()["yours"]["elapsed"] is None


@pytest.mark.parametrize(("text", "applied"), [
    ("They said 7 days but it has been 3 weeks, learner licence KA-05", "2026-09-17"),  # the wait, not the promise
    ("30 days late", None), ("a 30 day limit", None), ("10 marriage certificates", None), ("3 decisions", None),
    ("applied 20 days back", "2026-09-18"), ("12th of September", "2026-09-12"),
])
def test_durations_are_dates_only_when_they_mean_time_since_applying(text: str, applied: str | None) -> None:
    found, _ = ask.find_date(text, TODAY)
    assert (found.isoformat() if found else None) == applied


def test_leap_day_and_words_that_only_look_like_services() -> None:
    assert ask.find_date("29 Feb", date(2028, 1, 10)) == (None, "")  # no crash; 29 Feb 2027 doesn't exist
    assert ask.find_service("I'll apply for my DL soon") == "driving-licence"
    assert ask.find_intent("KA-05 RTO number plate") == "reach" and ask.find_service("bought a house") is None


@pytest.mark.parametrize("text", ["I live in the east", "Mrs Rao applied for marriage certificate", "Sri Lakshmi sale deed",
                                  "I bought a house and my sale deed registration is pending", "Bangalore city RTO"])
def test_sentences_without_an_office_name_pick_no_office(text: str) -> None:
    assert ask.understand(text, TODAY)["office"] is None


def test_naming_an_office_outright_wins_a_tie() -> None:
    assert ask.understand("sale deed at Jala Sub-Registrar Office", TODAY)["office"]["id"] == "sro-jala"


def test_a_wait_just_past_the_limit_allows_for_public_holidays() -> None:
    from kalaana import views
    assert views.wait_status(7, 7) == "within" and views.wait_status(9, 7) == "near" and views.wait_status(11, 7) == "past"


@pytest.mark.parametrize(("text", "applied", "service"), [
    ("Driving licence not received 40 days at Yeshwantpur", "2026-08-29", "driving-licence"),
    ("mera DL renewal yeshwanthpur rto mein 2 mahine se atka hai", "2026-08-09", "licence-renewal"),
    ("still waiting, applied 10 din pehle", "2026-09-28", None),
    ("lerners licence south rto", None, "learners-licence"),
])
def test_bare_durations_hinglish_and_common_misspellings(text: str, applied: str | None, service: str | None) -> None:
    found, _ = ask.find_date(text, TODAY)
    assert (found.isoformat() if found else None, ask.find_service(text)) == (applied, service)


def test_marriage_answers_carry_the_documents_condition() -> None:
    out = ask.answer("Rajajinagar sub registrar marriage certificate applied 3 weeks ago", TODAY)["answer"]
    assert "after the documents required under the Act and Rules are submitted" in out["headline"]
    assert out["headline"].endswith("if everything required was submitted when you applied.")
    assert any("Special Marriage Act" in line for line in out["lines"])


def test_a_service_without_an_office_asks_for_the_office() -> None:
    assert "Name it" in ask.answer("marriage certificate pending", TODAY)["understood"]["note"]


def test_the_claude_reader_stops_at_its_budget(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(reader, "SPEND_FILE", tmp_path / "spend.json")
    monkeypatch.setenv("KALAANA_ASK_BUDGET_USD", "0.001")
    assert reader.record_spend("claude-haiku-5-5", 1_000, 100) == pytest.approx(0.00015)  # 1k in, 100 out
    reader.record_spend("claude-haiku-5-5", 10_000, 0)  # now 0.00115, over 0.001
    with pytest.raises(reader.ReaderError, match="budget"):
        reader._anthropic("system", "message", ["learners-licence"])
    assert reader.spent()["calls"] == 2


@pytest.mark.parametrize("ledger", ["", "{", "[]", '{"usd": "x", "calls": 1}', '{"calls": 3}', '{"usd": NaN, "calls": 1}'])
def test_a_damaged_spend_ledger_stops_paid_calls(monkeypatch: pytest.MonkeyPatch, tmp_path, ledger: str) -> None:
    monkeypatch.setattr(reader, "SPEND_FILE", tmp_path / "spend.json")
    (tmp_path / "spend.json").write_text(ledger)
    with pytest.raises(reader.ReaderError, match="budget"):
        reader._anthropic("system", "message", ["learners-licence"])


@pytest.mark.parametrize("budget", ["nan", "inf", "-1", "ten"])
def test_an_unreadable_budget_allows_no_paid_calls(monkeypatch: pytest.MonkeyPatch, tmp_path, budget: str) -> None:
    monkeypatch.setattr(reader, "SPEND_FILE", tmp_path / "spend.json")
    monkeypatch.setenv("KALAANA_ASK_BUDGET_USD", budget)
    assert reader.budget_usd() == 0.0
    with pytest.raises(reader.ReaderError, match="budget"):
        reader._anthropic("system", "message", ["learners-licence"])


def test_the_spend_ledger_is_replaced_whole(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(reader, "SPEND_FILE", tmp_path / "spend.json")
    for _ in range(3):
        reader.record_spend("claude-haiku-5-5", 1_000, 0)
    assert reader.spent() == {"usd": pytest.approx(0.0003), "calls": 3}
    assert [p.name for p in tmp_path.iterdir()] == ["spend.json"]  # no temp files left behind


def test_a_failed_ledger_write_stops_further_paid_calls(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(reader, "SPEND_FILE", tmp_path / "spend.json")
    monkeypatch.setattr(reader, "_ledger_failed", False)

    def fail(*_: object) -> float:
        raise OSError("disk full")
    monkeypatch.setattr(reader, "record_spend", fail)
    reader.record_quietly("claude-haiku-5-5", 10, 10)
    with pytest.raises(reader.ReaderError, match="ledger"):
        reader._anthropic("system", "message", ["learners-licence"])


def test_any_reader_failure_falls_back_to_the_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_: object) -> None:
        raise TypeError("an SDK bug")
    monkeypatch.setattr(reader, "read", broken)
    got = ask.understand("learner's licence at KA-05 applied 3 weeks ago", TODAY)
    assert got["by"] == "rules" and got["office"]["id"] == "rto-ka05" and "rules read it" in got["note"]


@pytest.mark.parametrize("text", ["I live in Whitefield, my new passport applied 40 days ago",
                                  "we stay near Jalahalli and my passport is pending"])
def test_where_someone_lives_is_not_the_office(text: str) -> None:
    assert ask.understand(text, TODAY)["office"] is None


@pytest.mark.parametrize("text, office", [("passport at RPO Bengaluru number", "rpo-bengaluru"),
                                          ("regional passport office phone number", "rpo-bengaluru"),
                                          ("POPSK appointment", "popsk-jalahalli"),
                                          ("passport reissue at Whitefield PSK 3 weeks ago", "psk-whitefield")])
def test_passport_offices_by_kind_or_name(text: str, office: str) -> None:
    assert ask.understand(text, TODAY)["office"]["id"] == office


def test_a_reissue_headline_states_its_police_verification_assumption() -> None:
    got = ask.answer("passport reissue at PSK Lalbagh applied 3 weeks ago still waiting", TODAY)
    assert "assumes no police verification" in got["answer"]["headline"]


def test_cache_reads_are_priced_at_a_tenth_and_writes_at_a_quarter_more(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(reader, "SPEND_FILE", tmp_path / "spend.json")
    # Haiku 5.5: $0.10 per million input. 1M cache-read tokens cost $0.01; 1M cache-write tokens $0.125.
    assert reader.record_spend("claude-haiku-5-5", 0, 0, cache_read=1_000_000) == pytest.approx(0.01)
    assert reader.record_spend("claude-haiku-5-5", 0, 0, cache_write=1_000_000) == pytest.approx(0.135)


@pytest.mark.parametrize("text, office, service", [
    ("मेरा लर्नर लाइसेंस RTO साउथ में 3 हफ्ते से अटका है", "rto-ka05", "learners-licence"),
    ("ನನ್ನ ಡ್ರೈವಿಂಗ್ ಲೈಸೆನ್ಸ್ ನವೀಕರಣ ಯಲಹಂಕ ಆರ್‌ಟಿಒ ನಲ್ಲಿ ಒಂದು ತಿಂಗಳಿಂದ ಬಾಕಿ ಇದೆ", "rto-ka50", "licence-renewal"),
    ("पासपोर्ट लालबाग PSK में ५ हफ्ते पहले रिन्यू के लिए दिया, नहीं आया", "psk-lalbagh", "passport-reissue"),
])
def test_hindi_and_kannada_are_read_without_a_model(text: str, office: str, service: str) -> None:
    got = ask.understand(text, TODAY)
    assert got["office"]["id"] == office and got["service"] == service and got["applied"] and got["intent"] == "late"
