"""Matching Google Maps listings to official offices.

The listings here are hand-made test fixtures shaped like SerpApi's google_maps results.
They are not real data. The official offices come from data/official.
"""

from typing import Any

import pytest

from kalaana import official
from kalaana.offices import OFFICE_TYPES, Listing, match, place_names, score

RTO = OFFICE_TYPES["rto"]


@pytest.fixture(scope="module")
def rtos() -> list[official.Office]:
    return official.load().offices_of("rto")


def place(title: str, address: str = "", **extra: Any) -> dict[str, Any]:
    data_id = "0x" + "".join(f"{ord(c):x}" for c in title)[:16]  # stable across runs, unlike hash()
    return {"data_id": data_id, "place_id": "p", "title": title, "address": address,
            "type": "Department of motor vehicles", **extra}


def listing(title: str, address: str = "", **extra: Any) -> Listing:
    return Listing.from_maps(place(title, address, **extra), "test", "search-1")


def test_from_maps_search_result() -> None:
    l = listing("RTO X", "Bengaluru, Karnataka 560108", phone="080 2663 0989", unclaimed_listing=True,
                reviews=240, operating_hours={"monday": "10 am"})
    assert l.phone.key == "+918026630989" and l.unclaimed and l.reviews == 240 and l.has_hours
    assert l.pincode == "560108" and l.category == "Department of motor vehicles"


def test_from_maps_place_result_lists_categories() -> None:
    l = Listing.from_maps({"data_id": "0x1", "title": "RTO", "type": ["Department of motor vehicles", "Government office"]}, "q", "s")
    assert l.category == "Department of motor vehicles"


def test_absent_unclaimed_flag_is_not_read_as_claimed() -> None:
    assert listing("RTO X").unclaimed is False  # "not marked unclaimed", reported as such


def test_place_names_include_aliases(rtos: list[official.Office]) -> None:
    by_id = {o.id: o for o in rtos}
    assert place_names(by_id["rto-ka53"])[:2] == ["K.R. Puram", "Krishnarajapura"]
    assert place_names(by_id["rto-ka05"]) == ["Anjanapura"]


def test_score_explains_every_point(rtos: list[official.Office]) -> None:
    ka05 = next(o for o in rtos if o.id == "rto-ka05")
    m = score(listing("Regional Transport Office (KA 05)", "J. P. Nagar, Bengaluru, Karnataka 560108",
                      phone="080 2663 0989"), ka05)
    assert m.evidence == ("phone", "code", "pin") and m.score == 8 and m.strong
    assert len(m.reasons) == len(m.evidence)


def test_place_names_match_whole_words_only(rtos: list[official.Office]) -> None:
    ka50 = next(o for o in rtos if o.id == "rto-ka50")
    assert score(listing("RTO near Yelahanka", "Bengaluru"), ka50).evidence == ("title",)
    assert score(listing("RTO", "Yelahanka New Town, Bengaluru"), ka50).evidence == ("place",)
    assert score(listing("RTO", "NewYelahankaNagar, Bengaluru"), ka50).evidence == ()


def test_a_place_in_the_title_beats_a_shared_pin() -> None:
    """The Dasanapura office's listing carries the Madanayakanahalli office's PIN in its address."""
    sros = official.load().offices_of("subregistrar")
    result = match([listing("Sub Registrar Office, Dasanapura", "No.33, 4, Devannapalya, Dasanapura, Karnataka 562162", type="Government office")],
                   sros, OFFICE_TYPES["subregistrar"])
    assert list(result.matched) == ["sro-dasanapura"]


def test_match_assigns_roles(rtos: list[official.Office]) -> None:
    listings = [
        listing("Regional Transport Office, HSR Layout (Bengaluru Central) KA-01", "HSR Layout, Bengaluru 560102", reviews=762),
        listing("Example Motors (RTO Services in Bangalore)", "HSR Layout, Bengaluru 560102", reviews=826, phone="099999 00000"),
        listing("RTO ELECTRONIC CITY ADTT", "Electronic City, Karnataka 560099", reviews=796),
        listing("Electronic City (KA-51) RTO Office", "Devarachikkana Halli, Bengaluru 560076", reviews=1013),
    ]
    result = match(listings, rtos, RTO)
    roles = {l.title.split()[0]: m.role for oid in result.matched for l, m in result.matched[oid]}
    assert roles == {"Regional": "office", "Example": "private", "RTO": "facility", "Electronic": "office"}
    # The agent has more reviews, but the primary listing is always the office's own.
    assert result.primary("rto-ka01").title.startswith("Regional Transport Office, HSR")
    assert result.primary("rto-ka51").title.startswith("Electronic City (KA-51)")


def test_location_only_match_needs_an_office_like_title(rtos: list[official.Office]) -> None:
    result = match([listing("Sri Ganesh Xerox", "Anjanapura, Bengaluru 560108")], rtos, RTO)
    assert not result.matched and "no official office" in result.unmatched[0][1]


@pytest.mark.parametrize(
    ("title", "category", "why"),
    [
        ("Karnataka Office of the Commissioner for Transport", "Department of motor vehicles", "same department"),
        ("RTO Battarhalli", "Auto repair shop", "Auto repair shop"),
        ("RTO Office Vishweshwaraiah Layout", "Bus stop", "Bus stop"),
    ],
)
def test_non_offices_are_set_aside_with_a_reason(rtos: list[official.Office], title: str, category: str, why: str) -> None:
    result = match([listing(title, "Rajajinagar, Bengaluru 560010", type=category)], rtos, RTO)
    assert not result.matched and why in result.unmatched[0][1]


def test_unconfirmed_and_missing(rtos: list[official.Office]) -> None:
    # A location-only match leaves the office unconfirmed (worth a targeted search) but not missing.
    result = match([listing("Mallata Halli RTO office", "Jnana Ganga Nagar, Bengaluru 560091")], rtos, RTO)
    assert "rto-ka41" in {o.id for o in result.unconfirmed(rtos)}
    assert "rto-ka41" not in {o.id for o in result.missing(rtos)}
    assert "rto-ka59" in {o.id for o in result.missing(rtos)}


def test_a_tie_on_location_goes_to_the_office_whose_address_matches() -> None:
    """Ganganagara and Hebbala share PIN 560032; '7, 80 Feet Rd, HMT Layout' is Hebbala's official address."""
    sros = official.load().offices_of("subregistrar")
    found = listing("Sub-Registrar Office", "7, 80 Feet Rd, V . V Nagar, HMT Layout, 1st Sector, RT Nagar, Bengaluru, Karnataka 560032",
                    type="Government office")
    assert list(match([found], sros, OFFICE_TYPES["subregistrar"]).matched) == ["sro-hebbala"]
