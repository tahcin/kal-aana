"""Office types, cities, Google Maps listings, and matching listings to official offices.

The official directory (data/official) defines which offices exist. Each Google Maps listing a
sweep finds is matched to one of them, or kept aside with the reason it wasn't. A matched
listing has a role:

- office:   where citizens deal with the office. The most-reviewed one is the primary listing.
- facility: part of the office but not its front desk, e.g. a driving-test track or parking.
- private:  a private business trading on the office's name next door, e.g. "RTO Services".
            Reported (citizens find these first), never treated as the office.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Final, Literal

from . import phones
from .official import Office

INDIA: Final = {"hl": "en", "gl": "in", "google_domain": "google.co.in"}

Role = Literal["office", "facility", "private"]


@dataclass(frozen=True)
class City:
    name: str
    ll: str  # Maps viewport, "@lat,lng,zoom"
    location: str  # Google Search `location`
    std_code: str  # trunk code without the leading 0


CITIES: Final = {
    "Bengaluru": City("Bengaluru", "@12.9716,77.5946,11z", "Bengaluru,Karnataka,India", "80"),
}


@dataclass(frozen=True)
class OfficeType:
    id: str
    label: str
    maps_queries: tuple[str, ...]
    # Google Maps categories a listing of this office type can carry. Anything else (an auto
    # repair shop, a bus stop, a travel agency) is not the office, whatever its title says.
    maps_categories: frozenset[str]
    # A listing must look like this office type to be matched on location alone (PIN, place name).
    looks_like: re.Pattern[str]
    # Same department, but not an office citizens apply at (the Commissioner, a ministry).
    not_an_office: re.Pattern[str]
    facility: re.Pattern[str]
    private: re.Pattern[str]
    # Review keyword filters for targeted evidence. These samples are biased by design, so they
    # supply quotes and never count towards the shares of the issue mix.
    review_queries: tuple[str, ...]
    # Put before an office's name in a targeted search when the name alone is just a place
    # ("Malleshwaram"); RTO names already say what they are ("RTO Yelahanka").
    search_prefix: str = ""
    # How the product talks about this office type.
    short: str = ""  # "RTO"
    plural: str = ""  # "RTOs"
    nav: str = ""  # its link in the site's header: "Sub-registrars"
    department: str = ""  # who publishes the directory: "Transport Department"
    officer: str = ""  # whom a complaint letter is addressed to
    name_suffix: str = ""  # appended to a bare place name for display: "Malleshwaram" -> "... Sub-Registrar Office"
    # Where the time limits come from. A state law for Karnataka's offices; a central government charter for passports.
    # A title that only the government office should carry. Listings in the city with such a title that aren't
    # one of the official offices are "lookalikes": agents and cafes named like the office.
    official_name: re.Pattern[str] | None = None
    promise: str = "the law"
    promise_name: str = "Karnataka Sakala Services Act, 2011"


OFFICE_TYPES: Final = {
    "rto": OfficeType(
        id="rto",
        label="Regional Transport Office",
        maps_queries=("Regional Transport Office",),
        maps_categories=frozenset({
            "", "Department of motor vehicles", "Regional government office", "Government office",
            "Driver's license office", "Driving test center", "License bureau", "Public parking space",
            "Association / Organization",  # a category agents use; `private` then decides the role
        }),
        looks_like=re.compile(r"\bA?R\.?\s?T\.?\s?O\b|regional transport|transport office|motor vehicles", re.I),
        not_an_office=re.compile(r"commissioner|ministry|directorate|driving school|insurance", re.I),
        facility=re.compile(r"\bADTT\b|test track|driving track|driving test|parking", re.I),
        private=re.compile(r"\bservices?\b|\bonline\b|\bworks\b|consultan|\bagen(?:t|cy)\b", re.I),
        review_queries=("phone", "bribe", "agent"),
        short="RTO",
        plural="RTOs",
        nav="RTOs",
        department="Transport Department",
        officer="Regional Transport Officer",
    ),
    "subregistrar": OfficeType(
        id="subregistrar",
        label="Sub-Registrar Office",
        maps_queries=("Sub Registrar Office",),
        maps_categories=frozenset({"", "Government office", "Registry office", "Registration office",
                                   "State government office", "Local government office", "Regional government office",
                                   "Land registry office", "Marriage license bureau", "Association / Organization"}),
        looks_like=re.compile(r"sub[\s-]?regist|\bS\.?R\.?O\b|registrar|registration office", re.I),
        not_an_office=re.compile(r"(?<!additional )district registrar|inspector general|\bIGR\b|commissioner|ministry|"
                                 r"marriage hall|bank", re.I),
        facility=re.compile(r"parking", re.I),
        private=re.compile(r"\bservices?\b|\bonline\b|consultan|\bagen(?:t|cy)\b|document\s+writer|deed\s+writer|"
                           r"\badvocate|\blawyer|\bnotary|associates|\blegal\b|\bstamp\s+vendor", re.I),
        review_queries=("phone", "bribe", "agent"),
        search_prefix="Sub Registrar Office ",
        short="sub-registrar office",
        plural="sub-registrar offices",
        nav="Sub-registrars",
        department="Department of Stamps and Registration",
        officer="Sub-Registrar",
        name_suffix=" Sub-Registrar Office",
    ),
    "passport": OfficeType(
        id="passport",
        label="Passport Office",
        maps_queries=("Passport Seva Kendra", "Passport Office"),
        maps_categories=frozenset({"", "Passport office", "Government office", "Regional government office",
                                   "Federal government office", "Central government office", "Post office",
                                   "Association / Organization"}),
        looks_like=re.compile(r"passport|\bP\.?S\.?K\b|\bR\.?P\.?O\b", re.I),
        not_an_office=re.compile(r"police|embassy|consulate|\bVFS\b|visa (?:application|facilitation)|"
                                 r"ministry|photo|studio", re.I),
        facility=re.compile(r"parking|\bpark\b", re.I),
        private=re.compile(r"\bservices?\b|\bonline\b|consultan|\bagen(?:t|cy)\b|travels?\b|tours?\b|\bvisa\b|"
                           r"xerox|cyber|associates|solutions?\b|renewal|\bapply\b|\bG\s?S\b", re.I),
        review_queries=("phone", "agent", "verification"),
        short="passport office",
        plural="passport offices",
        nav="Passport",
        department="Ministry of External Affairs",
        officer="Regional Passport Officer",
        official_name=re.compile(r"passport\s+se[vw]a\s+kendra|passport\s+office|regional\s+passport", re.I),
        promise="the Citizen's Charter",
        promise_name="Passport Seva Citizen's Charter (Ministry of External Affairs)",
    ),
}

# "KA-05", "KA 05", "KA05", "(KA 5)"
_RTO_CODE = re.compile(r"\bKA\s?-?\s?0?(\d{1,2})\b", re.I)
_PINCODE = re.compile(r"(?<!\d)(5\d{2})\s?(\d{3})(?!\d)")


@dataclass(frozen=True)
class Listing:
    """A Google Maps place as returned by the google_maps search engine."""

    data_id: str
    place_id: str
    title: str
    address: str = ""
    phone: phones.Phone | None = None
    phone_raw: str = ""
    website: str = ""
    rating: float | None = None
    reviews: int = 0
    category: str = ""  # Google's primary category, the `type` field
    has_hours: bool = False
    # Google marks listings nobody has claimed. The flag is either true or absent, so absent
    # means "not marked unclaimed", which is not proof that the office claimed it.
    unclaimed: bool = False
    lat: float | None = None
    lng: float | None = None
    found_by: str = ""  # the Maps query that surfaced it
    search_id: str = ""

    @classmethod
    def from_maps(cls, place: dict[str, Any], found_by: str, search_id: str) -> Listing:
        gps = place.get("gps_coordinates") or {}
        raw = place.get("phone") or ""
        category = place.get("type") or ""
        if isinstance(category, list):  # place results list every category; search results give the primary
            category = category[0] if category else ""
        return cls(
            data_id=place["data_id"],
            place_id=place.get("place_id", ""),
            title=place.get("title", ""),
            address=place.get("address", ""),
            phone=phones.parse(raw),
            phone_raw=raw,
            website=place.get("website", ""),
            rating=place.get("rating"),
            reviews=int(place.get("reviews") or 0),
            category=category,
            has_hours=bool(place.get("operating_hours") or place.get("hours")),
            unclaimed=place.get("unclaimed_listing") is True,
            lat=gps.get("latitude"),
            lng=gps.get("longitude"),
            found_by=found_by,
            search_id=search_id,
        )

    @property
    def pincode(self) -> str:
        matches = _PINCODE.findall(self.address)
        return "".join(matches[-1]) if matches else ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["phone"] = self.phone.key if self.phone else ""
        return d


Evidence = Literal["phone", "code", "pin", "title", "place"]
# A place name in the listing's title says which office it is; in the address it may only be the
# neighbourhood (the Dasanapura office's listing has the PIN of the Madanayakanahalli office).
POINTS: Final[dict[Evidence, int]] = {"phone": 3, "code": 3, "pin": 2, "title": 3, "place": 2}


@dataclass(frozen=True)
class Match:
    office_id: str
    evidence: tuple[Evidence, ...]
    reasons: tuple[str, ...]  # one human-readable reason per piece of evidence
    role: Role = "office"

    @property
    def score(self) -> int:
        return sum(POINTS[e] for e in self.evidence)

    @property
    def strong(self) -> bool:
        """Matched on a shared phone number or the office code, not just location."""
        return "phone" in self.evidence or "code" in self.evidence


@dataclass
class MatchResult:
    matched: dict[str, list[tuple[Listing, Match]]] = field(default_factory=dict)  # office id -> listings
    unmatched: list[tuple[Listing, str]] = field(default_factory=list)  # listing, why not

    def listings_for(self, office_id: str) -> list[tuple[Listing, Match]]:
        """An office's listings: offices, then facilities, then private businesses; most-reviewed first."""
        order = {"office": 0, "facility": 1, "private": 2}
        return sorted(self.matched.get(office_id, []), key=lambda lm: (order[lm[1].role], -lm[0].reviews))

    def primary(self, office_id: str) -> Listing | None:
        """The office's own listing that citizens most likely find: its most-reviewed one."""
        offices = [l for l, m in self.listings_for(office_id) if m.role == "office"]
        return offices[0] if offices else None

    def unconfirmed(self, offices: list[Office]) -> list[Office]:
        """Official offices with no listing of their own matched on a phone number or the office code."""
        return [o for o in offices if not any(m.role == "office" and m.strong for _, m in self.matched.get(o.id, []))]

    def missing(self, offices: list[Office]) -> list[Office]:
        """Official offices with no listing of their own (facilities and private ones don't count)."""
        return [o for o in offices if self.primary(o.id) is None]


_GENERIC_NAME_WORDS: Final = frozenset({"rto", "arto", "bengaluru", "bangalore", "north", "south", "east", "west", "central", "stu", "and",
                                        "regional", "passport", "office", "seva", "sewa", "kendra", "post"})


def place_names(office: Office) -> list[str]:
    """Place names for an office: from its official name ('RTO K.R. Puram' -> 'K.R. Puram') plus our aliases."""
    places = []
    for part in re.split(r"[(),]", office.name):
        words = [w for w in part.split() if w.lower().strip(".") not in _GENERIC_NAME_WORDS]
        if words and all(w[0].isupper() for w in words):
            places.append(" ".join(words))
    return places + list(office.aliases)


def score(listing: Listing, office: Office) -> Match:
    """How strongly a Maps listing corresponds to an official office. Every point has a reason."""
    found: list[tuple[Evidence, str]] = []
    if listing.phone and listing.phone.key in office.phone_keys:
        found.append(("phone", f"phone {listing.phone.display} is in the official directory"))
    code = _RTO_CODE.search(listing.title)
    if office.code and code and f"KA-{int(code.group(1)):02d}" == office.code:
        found.append(("code", f"title names {office.code}"))
    if office.pincode and listing.pincode == office.pincode:
        found.append(("pin", f"same PIN {office.pincode}"))
    def mentions(text: str) -> list[str]:
        return [p for p in place_names(office) if re.search(rf"(?<!\w){re.escape(p)}(?!\w)", text, re.I)]

    if in_title := mentions(listing.title):
        found.append(("title", f"title mentions {in_title[0]}"))
    elif in_address := mentions(listing.address):
        found.append(("place", f"mentions {in_address[0]}"))
    return Match(office.id, tuple(e for e, _ in found), tuple(r for _, r in found))


def address_overlap(a: str, b: str) -> int:
    """Distinctive words two addresses share (house numbers and street names, not "Bengaluru")."""
    def words(text: str) -> set[str]:
        return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _ADDRESS_NOISE and not re.fullmatch(r"5\d{5}", w)}
    return len(words(a) & words(b))


_ADDRESS_NOISE: Final = frozenset({"bengaluru", "bangalore", "karnataka", "india", "road", "rd", "main", "cross", "floor",
                                   "office", "sub", "registrar", "registrars", "s", "the", "of", "and", "no", "near", "opp",
                                   "post", "1st", "2nd", "3rd", "layout", "nagar", "stage", "block", "building"})


def _role(listing: Listing, office_type: OfficeType) -> Role:
    if office_type.private.search(listing.title):
        return "private"
    if office_type.facility.search(listing.title) or listing.category in ("Driving test center", "Public parking space"):
        return "facility"
    return "office"


def match(listings: list[Listing], offices: list[Office], office_type: OfficeType) -> MatchResult:
    """Assign each listing to its best-scoring official office, or say why it has none.

    A shared phone number or the office code in the title is enough on its own. Location
    evidence alone (same PIN, or the office's place name) counts only for a listing whose
    title looks like this office type.
    """
    result = MatchResult()
    for listing in listings:
        if office_type.not_an_office.search(listing.title):
            result.unmatched.append((listing, "same department, but not an office citizens apply at"))
            continue
        if listing.category not in office_type.maps_categories:
            result.unmatched.append((listing, f"Google lists it as '{listing.category}'"))
            continue
        # Ties (two offices with the same PIN) go to the office whose official address shares the most
        # words with the listing's: "7, 80 Feet Rd, HMT Layout" is Hebbala's address, not Ganganagara's.
        by_id = {o.id: o for o in offices}
        best = max((score(listing, o) for o in offices),
                   key=lambda m: (m.score, address_overlap(listing.address, by_id[m.office_id].address)), default=None)
        if best and (best.strong or (best.score > 0 and office_type.looks_like.search(listing.title))):
            result.matched.setdefault(best.office_id, []).append((listing, replace(best, role=_role(listing, office_type))))
        else:
            why = "; ".join(best.reasons) if best and best.reasons else "shares no phone, code, PIN or place name"
            result.unmatched.append((listing, f"no official office in this city matched ({why})"))
    return result
