from collections import Counter
from pathlib import Path

import pytest

from kalaana import official


@pytest.fixture(scope="module")
def data() -> official.OfficialData:
    return official.load()


def write(tmp_path: Path, body: str) -> Path:
    (tmp_path / "x.toml").write_text(body)
    return tmp_path


RTO_META = '[meta]\noffice_type = "rto"\nsource_url = "https://example.gov.in"\n'


# The shipped data


def test_every_row_has_a_source(data: official.OfficialData) -> None:
    assert data.offices and data.timelines
    for row in [*data.offices.values(), *data.timelines.values()]:
        assert row.source_url.startswith("https://"), row.id


def test_directory_sizes_match_the_published_pages(data: official.OfficialData) -> None:
    # 12 offices in the Bengaluru Urban table plus KA-52; 43 offices under the 5 Bengaluru DROs.
    assert len(data.offices_of("rto")) == 13
    assert len(data.offices_of("subregistrar")) == 43
    assert len(data.offices_of("passport")) == 4


def test_phone_labels_match_their_directory_columns(data: official.OfficialData) -> None:
    for o in data.offices_of("rto"):
        assert {official.LANDLINE, official.CUG} <= {p.label for p in o.phones}, o.id
    for o in data.offices_of("subregistrar"):
        assert o.phones and all(p.phone.kind == "mobile" for p in o.phones), o.id
    for o in data.offices.values():
        for p in o.phones:
            assert p.phone.kind == ("landline" if p.label == official.LANDLINE else "mobile"), (o.id, p)


def test_no_number_is_listed_for_two_offices(data: official.OfficialData) -> None:
    """Unless the source itself does so and the data says so: the passport site gives POPSK Jalahalli the RPO's line."""
    counts = Counter(k for o in data.offices.values() for k in o.phone_keys)
    shared = [k for k, n in counts.items() if n > 1]
    owners = {k: [o for o in data.offices.values() if k in o.phone_keys] for k in shared}
    assert all(any("main line" in note for o in offices for note in o.notes) for offices in owners.values()), owners
    assert shared == ["+918025706100"]


def test_every_office_has_a_pincode_or_says_why_not(data: official.OfficialData) -> None:
    for o in data.offices.values():
        assert o.pincode or any("PIN" in n for n in o.notes), o.id


def test_owners_office_and_timeline(data: official.OfficialData) -> None:
    ka05 = data.offices["rto-ka05"]
    assert ka05.code == "KA-05" and ka05.pincode == "560108" and ka05.group == "Bengaluru Urban"
    assert "+918026630989" in ka05.phone_keys
    ll = data.timelines["learners-licence"]
    assert (ll.days, ll.unit) == (7, "working days") and ll.citation.endswith("#page=55")
    assert data.appeals["rto"].first_appeal == "Joint Commissioner for Transport"
    assert data.helplines["rto"].key == "+919449863459"


def test_subregistrar_timelines_and_appeals(data: official.OfficialData) -> None:
    assert {t.id for t in data.timelines_for("subregistrar")} >= {"property-registration", "encumbrance-certificate"}
    assert data.timelines["marriage-registration-hindu"].unit == "days"
    assert data.appeals["subregistrar"].first_appeal == "District Registrar"


def test_ambiguous_number_resolved_by_its_column(data: official.OfficialData) -> None:
    # libphonenumber can't tell whether 7795444664 is a mobile or a landline; the column can.
    [p] = data.offices["sro-hesaraghatta"].phones
    assert p.phone.kind == "mobile"


def test_published_typos_are_kept_as_notes(data: official.OfficialData) -> None:
    ka53 = data.offices["rto-ka53"]
    assert any("94449863453" in n for n in ka53.notes)
    assert all(len(k) == 13 for k in ka53.phone_keys)  # +91 and 10 digits


def test_passport_timelines(data: official.OfficialData) -> None:
    fresh = data.timelines["passport-fresh"]
    assert fresh.days == 30 and "police verification" in fresh.excludes and fresh.office_type == "passport"
    assert data.timelines["passport-tatkaal"].excludes == ""
    assert fresh.citation == fresh.source_url  # no page number recorded
    assert data.helplines["passport"].kind == "toll_free"


def test_every_timeline_has_offices_of_its_type(data: official.OfficialData) -> None:
    for t in data.timelines.values():
        assert data.offices_of(t.office_type), t.id


# Pincode extraction


@pytest.mark.parametrize(
    ("address", "pincode"),
    [
        ("Survey No 512 345, Anekal 562106", "562106"),
        ("Gandhibazar Main Road, Bangalore 560 004", "560004"),
        ("Jayanagar, Bengaluru- 56001", ""),
        ("No. 5600123, Somewhere", ""),
    ],
)
def test_pincode_is_the_last_six_digit_pin(address: str, pincode: str) -> None:
    assert official.Office("x", "rto", "X", "https://x", address=address).pincode == pincode


# Strict loading


@pytest.mark.parametrize(
    ("body", "error"),
    [
        (RTO_META + '[[office]]\nid = "x"\nname = "X"\nlandlines = ["080-123"]\n', "080-123"),
        (RTO_META + '[[office]]\nid = "x"\nname = "X"\nlandlines = ["9449864005"]\n', "expected landline"),
        (RTO_META + '[[office]]\nid = "x"\nname = "X"\ncug = ["080-26630989"]\n', "expected mobile"),
        (RTO_META + '[[office]]\nid = "x"\nname = "X"\nlandline = ["080-26630989"]\n', "unknown key"),
        (RTO_META + '[[office]]\nid = "x"\n', "missing name"),
        (RTO_META + '[[office]]\nid = "x"\nname = "X"\n[[office]]\nid = "x"\nname = "Y"\n', "duplicate office"),
        ('[meta]\noffice_type = "rto"\n[[office]]\nid = "x"\nname = "X"\n', "no source_url"),
        ('[meta]\nsource_url = "https://x"\n[[office]]\nid = "x"\nname = "X"\n', "no office_type"),
        (RTO_META + '[[service]]\nid = "s"\nname = "S"\ndays = 7.5\n', "positive integer"),
        (RTO_META + '[[service]]\nid = "s"\nname = "S"\ndays = "7"\n', "positive integer"),
        (RTO_META + '[[service]]\nid = "s"\nname = "S"\ndays = 7\npage = true\n', "page must be"),
        (RTO_META + '[[service]]\nid = "s"\nname = "S"\n', "days must be"),
        (RTO_META + '[appeals.rto]\nfirst_appeal = "X"\n', "appeals.rto"),
        (RTO_META + 'helpline = "123"\n', "not a valid Indian number"),
        ('[meta]\nofice_type = "rto"\n', "unknown key"),
    ],
)
def test_bad_data_is_rejected(tmp_path: Path, body: str, error: str) -> None:
    with pytest.raises(official.OfficialDataError, match=error):
        official.load(write(tmp_path, body))


def test_service_inherits_office_type_from_meta(tmp_path: Path) -> None:
    loaded = official.load(write(tmp_path, RTO_META + '[[service]]\nid = "s"\nname = "S"\ndays = 3\n'))
    assert loaded.timelines["s"].office_type == "rto" and loaded.timelines["s"].citation == "https://example.gov.in"


def test_national_helpline_is_recognised(data: official.OfficialData) -> None:
    # The Electronic City test-track listing on Maps shows this number.
    line = data.national["+911204925505"]
    assert "Parivahan" in line.name and line.source_url.startswith("https://parivahan.gov.in")
