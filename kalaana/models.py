"""The shape of a snapshot (data/snapshot/*.json): the contract between snapshot.py, which writes
it, and the web app, the JSON API and the MCP server, which read it. tests/test_snapshot.py checks
the committed snapshots against these models.
"""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

Verdict = Literal["this office", "regional office", "another office", "national helpline", "department helpline",
                  "not in the directory"]


class Quote(TypedDict):
    review_id: str
    text: str  # masked: no names, no private mobiles
    evidence: str  # the words that matched, highlighted in the text
    language: str
    date: str
    rating: float | None
    sample: str  # "newest", or "query:<keyword>" for a keyword-filtered page
    link: str  # the review on Google Maps


class Issue(TypedDict):
    category: str
    label: str
    polarity: Literal["problem", "positive"]
    count: int  # recent reviews reporting it
    of: int  # the denominator: recent reviews with text
    quotes: list[Quote]


class Check(TypedDict):
    id: str
    label: str
    max_points: int
    passed: bool | None  # None: couldn't be decided, so left out of the score
    detail: str
    points: int


class Reach(TypedDict):
    score: int | None  # the listing score, 0-100; None if the office has no listing
    basis: str  # "5 of 6 checks"
    checks: list[Check]


class Breach(TypedDict):
    service: str
    service_id: str
    statutory_days: int
    unit: str
    citation: str
    reported_days: int
    reported_working_days: int
    said: str
    explanation: str
    quote: Quote


class Listing(TypedDict):
    """The office's primary Google Maps listing. The raw phone is never published."""

    data_id: str
    place_id: str
    title: str  # masked: some titles name a person
    address: str
    website: str
    rating: float | None
    reviews: int
    category: str
    has_hours: bool
    unclaimed: bool
    lat: float | None
    lng: float | None
    found_by: str
    search_id: str
    maps_url: str
    match: dict[str, Any]
    phone_display: NotRequired[str]  # masked when it may be private
    phone_verdict: NotRequired[Verdict]
    phone_detail: NotRequired[str]


class OtherListing(TypedDict):
    title: str
    role: Literal["office", "facility", "private"]
    reviews: int
    unclaimed: bool
    phone_display: str
    maps_url: str
    reasons: list[str]


class ShownNumber(TypedDict):
    phone: str  # the full number only when it is a directory number or a helpline; "" otherwise
    display: str
    kind: str
    surface: Literal["ai_overview", "ai_mode", "knowledge_graph", "local_pack", "snippet"]
    source: str
    verdict: Verdict
    detail: str


class AIOverview(TypedDict):
    text: str  # private mobiles masked
    first_number: ShownNumber | None
    searched_on: str
    numbers: list[ShownNumber]
    pincodes: list[str]
    address_matches: bool | None
    references: list[list[str]]  # [title, link]
    search_id: str
    query: str
    repeats_listing_number: bool  # its first number is the one on the office's Maps listing


class AIMode(TypedDict):
    """Google's AI Mode, asked the same question as the citizen's search."""
    text: str  # private mobiles masked
    first_number: ShownNumber | None
    searched_on: str
    numbers: list[ShownNumber]
    pincodes: list[str]
    address_matches: bool | None
    references: list[list[str]]  # [title, link]
    search_id: str


class Busy(TypedDict):
    """Google's typical busyness for the office's own place, by weekday and hour ("popular times")."""
    title: str  # the Google place it was shown for
    engine: str  # google (the knowledge panel) or google_maps (the place)
    search_id: str
    days: dict[str, list[list[int]]]  # "monday" -> [[hour 0-23, busyness 0-100], ...]; 0 = no visits shown


class BingCheck(TypedDict):
    """The office looked up on Bing Maps: is the missing number only Google's problem?"""
    found: bool  # a Bing place was taken to be this office
    title: str
    how: str  # why: "3 m from its Google Maps listing", "title names Yelahanka"
    search_id: str
    query: str
    phone_display: str  # "" when the place shows no phone; masked when not in the directory
    phone_verdict: Verdict | None


class CitizenSearch(TypedDict):
    query: str
    search_id: str
    numbers: list[ShownNumber]


class OfficialPhone(TypedDict):
    display: str
    label: str
    tel: str


class Step(TypedDict):
    """One SerpApi search behind a finding."""

    engine: str
    purpose: str
    search_id: str
    searched_at: str  # SerpApi's own timestamp, "2026-10-08 02:38 UTC"


class Office(TypedDict):
    id: str
    code: str
    name: str
    display_name: str
    office_type: str
    aliases: list[str]
    kind: str
    address: str
    pincode: str
    email: str
    source_url: str
    notes: list[str]
    official_phones: list[OfficialPhone]
    listing: Listing | None
    other_listings: list[OtherListing]
    reach: Reach
    sample_size: int
    window_reviews: int
    span: list[str] | None
    enough_evidence: bool
    problem_reviews: int
    positive_reviews: int
    sampled: bool  # False: reviews weren't read for this office (credits)
    searched_individually: bool
    citizen_checked: bool  # False: Google Search and the AI Overview weren't checked (Halasooru: the search failed)
    issues: list[Issue]
    breaches: list[Breach]
    agent_waits: list[Breach]
    older_breaches: int
    ai_overview: AIOverview | None
    ai_mode: AIMode | None
    bing: BingCheck | None
    citizen_search: CitizenSearch | None
    trail: list[Step]
    busy: Busy | None


class SharedNumber(TypedDict):
    display: str
    offices: list[str]
    names: list[str]


class Headline(TypedDict):
    offices: int
    official_phone: int
    official_landline: int
    listed: int
    not_found: list[str]
    listing_no_phone: int
    listing_official_phone: int
    listing_phone_shown: int
    listing_phone_not_in_directory: int
    shared_listing_numbers: list[SharedNumber]
    listing_unclaimed: int
    ai_overviews: int
    ai_first_number_right: int
    ai_address_wrong: list[str]
    ai_first_number_from_listing: int
    bing_checked: int
    bing_found: int
    bing_no_phone: int
    bing_official_phone: int
    ai_mode_answers: int
    ai_mode_first_number_right: int
    ai_mode_address_wrong: list[str]
    citizen_checked: int
    sampled: int
    recent_breaches: int
    enough_evidence: int


class Profile(TypedDict):
    label: str
    short: str
    plural: str
    department: str
    officer: str
    review_queries: list[str]
    directory_url: str
    promise: str  # where the time limits come from: "the law", "the Citizen's Charter"
    promise_name: str  # "Karnataka Sakala Services Act, 2011"


class Rules(TypedDict):
    issue_window_days: int
    min_sample: int
    recent_days: int
    breach_margin_pct: int


class Snapshot(TypedDict):
    city: str
    office_type: str
    profile: Profile
    as_of: str
    rules: Rules
    headline: Headline
    offices: list[Office]
    timelines: list[dict[str, Any]]
    appeals: dict[str, Any] | None
    helpline: str
    grievance: dict[str, Any] | None  # passport: the MEA's grievance portals, phones and email
    lookalikes: list[dict[str, Any]]  # listings named like the office that aren't one (title, category, PIN, reviews, lat, lng)
    unmatched: list[dict[str, str]]
    sweep: list[Step]
    searches_by_engine: dict[str, int]
    searches: int
