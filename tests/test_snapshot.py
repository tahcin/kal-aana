"""The committed snapshots: what the repository publishes must never expose a private number."""

import json
import re
from typing import Any, NotRequired, get_origin, get_type_hints

import pytest

from kalaana import models, official, phones, snapshot

SNAPSHOTS = sorted(snapshot.SNAPSHOT_DIR.glob("*.json"))


def _official_mobiles() -> set[str]:
    data = official.load()
    keys = {k for o in data.offices.values() for k in o.phone_keys} | set(data.national)
    keys |= {h.key for h in data.helplines.values()}
    return {k[-10:] for k in keys}


def full_mobiles(text: str) -> set[str]:
    """Every Indian mobile written out in full, however it's formatted: 9845012345, 098450 12345,
    +91 98450-12345, +919845012345."""
    joined = re.sub(r"(?<=\d)[\s\-.]+(?=\d)", "", text)
    found = set()
    for run in re.findall(r"(?<![0-9A-Za-z])\d{10,13}(?![0-9A-Za-z])", joined):  # not inside a hex search ID
        phone = phones.parse(run)  # libphonenumber tells a mobile from a landline such as 080 2663 0989
        if phone and phone.kind in ("mobile", "fixed_or_mobile"):
            found.add(phone.key[-10:])
    return found


ROOT = snapshot.SNAPSHOT_DIR.parent.parent
PUBLISHED = SNAPSHOTS + sorted((ROOT / "docs").glob("*.md")) + sorted(p for d in ("labels", "refined") for p in (ROOT / "data" / d).glob("*.jsonl")) + [ROOT / "README.md"]


@pytest.mark.parametrize("path", PUBLISHED, ids=lambda p: p.name)
def test_no_private_mobile_is_published_in_full(path) -> None:
    text = path.read_text(encoding="utf-8")
    leaked = full_mobiles(text) - _official_mobiles()
    assert not leaked, sorted(leaked)
    assert '"phone_raw"' not in text


def test_the_detector_catches_every_format() -> None:
    assert full_mobiles("a 9845012345 b 098450 12345 c +91 98450-12345 d +919845012345") == {"9845012345"}
    assert full_mobiles("080 2663 0989, 1800 258 1800, 98••• •••45, search 6ac70228b7022302706e") == set()


@pytest.mark.parametrize("path", SNAPSHOTS, ids=lambda p: p.stem)
def test_headline_adds_up(path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    h, offices = data["headline"], data["offices"]
    assert h["offices"] == len(offices)
    assert h["listed"] + len(h["not_found"]) == h["offices"]
    assert h["listing_no_phone"] + h["listing_phone_shown"] == h["listed"]
    assert h["listing_official_phone"] + h["listing_phone_not_in_directory"] <= h["listing_phone_shown"]
    assert h["ai_first_number_right"] <= h["ai_overviews"] <= h["citizen_checked"] <= h["offices"]
    assert data["searches"] == sum(data["searches_by_engine"].values())


def test_both_office_types_are_published() -> None:
    assert {p.stem for p in SNAPSHOTS} >= {"bengaluru-rto", "bengaluru-subregistrar"}


def _keys(model: type) -> tuple[set[str], set[str]]:
    hints = get_type_hints(model, include_extras=True)
    optional = {k for k, h in hints.items() if get_origin(h) is NotRequired}
    return set(hints) - optional, set(hints)


def _conforms(value: dict[str, Any], model: type, where: str) -> list[str]:
    required, allowed = _keys(model)
    problems = [f"{where}: missing {sorted(required - set(value))}"] if required - set(value) else []
    problems += [f"{where}: unexpected {sorted(set(value) - allowed)}"] if set(value) - allowed else []
    return problems


@pytest.mark.parametrize("path", SNAPSHOTS, ids=lambda p: p.stem)
def test_snapshot_matches_its_models(path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    problems = _conforms(data, models.Snapshot, "snapshot") + _conforms(data["headline"], models.Headline, "headline")
    problems += _conforms(data["profile"], models.Profile, "profile")
    for o in data["offices"]:
        problems += _conforms(o, models.Office, o["id"]) + _conforms(o["reach"], models.Reach, f"{o['id']}.reach")
        if o["listing"]:
            problems += _conforms(o["listing"], models.Listing, f"{o['id']}.listing")
        if o["ai_overview"]:
            problems += _conforms(o["ai_overview"], models.AIOverview, f"{o['id']}.ai_overview")
        for i in o["issues"]:
            problems += _conforms(i, models.Issue, f"{o['id']}.issue")
            problems += [p for q in i["quotes"] for p in _conforms(q, models.Quote, f"{o['id']}.quote")]
        problems += [p for b in o["breaches"] + o["agent_waits"] for p in _conforms(b, models.Breach, f"{o['id']}.breach")]
        problems += [p for l in o["other_listings"] for p in _conforms(l, models.OtherListing, f"{o['id']}.other")]
    assert not problems, problems[:10]
