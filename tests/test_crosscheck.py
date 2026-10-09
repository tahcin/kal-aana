"""The Bing Maps cross-check: which Bing place is the office, and what its phone is."""

from kalaana import official
from kalaana.crosscheck import bing_params, match, places
from kalaana.offices import CITIES

DATA = official.load()
KA05 = DATA.offices["rto-ka05"]
GOOGLE_AT = (12.865057, 77.5624405)  # KA-05's Google Maps listing


def place(title: str, lat: float, lng: float, **extra: str) -> dict[str, object]:
    return {"title": title, "gps_coordinates": {"latitude": lat, "longitude": lng}, **extra}


def test_query_is_the_office_name_centred_on_the_city() -> None:
    assert bing_params(KA05, CITIES["Bengaluru"]) == {
        "engine": "bing_maps", "q": "RTO Bengaluru South", "cp": "12.9716~77.5946"}


def test_places_reads_both_response_shapes() -> None:
    assert [p["title"] for p in places({"local_results": [{"items": [{"title": "A"}, {"title": "B"}]}]})] == ["A", "B"]
    assert [p["title"] for p in places({"place_results": {"title": "Only one"}})] == ["Only one"]
    assert places({}) == []


def test_the_office_is_the_nearby_place_that_looks_like_it() -> None:
    candidates = [
        place("RTO Consultant Joseph", 12.86506, 77.56244, type="Driving school"),  # right spot, but a private agent
        place("RTO ANJANAPURA KA 05", 12.865029, 77.562439, type="Department of motor vehicles"),
        place("RTO KA-03 Kasturi Nagar", 13.0, 77.66, type="Department of motor vehicles"),
    ]
    hit = match(KA05, candidates, GOOGLE_AT)
    assert hit and hit[0]["title"] == "RTO ANJANAPURA KA 05" and hit[1] == "3 m from its Google Maps listing"


def test_no_match_when_the_only_office_is_far_away_or_unnamed() -> None:
    far = [place("Karnataka Office of the Commissioner for Transport", 12.954, 77.592, type="Department of motor vehicles")]
    assert match(KA05, far, GOOGLE_AT) is None
    named = [place("RTO Anjanapura Office", 12.95, 77.59, type="Department of motor vehicles")]
    assert match(KA05, named, None) is not None  # no Google listing: fall back to the place name
