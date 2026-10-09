"""What Google tells a citizen who searches for an office's phone number.

One Google search per office ("<office> phone number", located in the city), plus the AI
Overview when Google defers it to a second request, plus the same question in Google's AI Mode.
Every phone number and PIN code Google shows (AI Overview, AI Mode, knowledge panel, local pack,
result snippets) is checked against the
official directory: is it this office's own number, another office's, a national queue, or
something else? Is the address Google's AI gives the office's current one?
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Final, Literal

from . import phones
from .client import BudgetExceeded, CacheMiss, SearchClient, SearchError
from .offices import INDIA, OFFICE_TYPES, City
from .official import Office, OfficialData

Surface = Literal["ai_overview", "ai_mode", "knowledge_graph", "local_pack", "snippet"]
Verdict = Literal["this office", "regional office", "another office", "national helpline", "department helpline",
                  "not in the directory"]

_PINCODE: Final = re.compile(r"(?<!\d)(5\d{2})\s?(\d{3})(?!\d)")


@dataclass(frozen=True)
class ShownNumber:
    phone: phones.Phone
    surface: Surface
    source: str  # where it came from: a result's domain, a local-pack title, "AI Overview"
    verdict: Verdict
    detail: str  # e.g. which other office it belongs to


@dataclass
class CitizenView:
    office_id: str
    query: str
    search_id: str = ""
    google_url: str = ""
    ai_text: str = ""  # the AI Overview, flattened to text
    ai_references: list[tuple[str, str]] = field(default_factory=list)  # (title, link)
    ai_pincodes: list[str] = field(default_factory=list)
    ai_followup: bool = False  # Google deferred the AI Overview: one more search fetched it
    searched_on: str = ""  # YYYY-MM-DD, from SerpApi's search metadata
    mode_search_id: str = ""  # Google's AI Mode, asked the same question
    mode_text: str = ""
    mode_references: list[tuple[str, str]] = field(default_factory=list)
    mode_pincodes: list[str] = field(default_factory=list)
    mode_searched_on: str = ""
    numbers: list[ShownNumber] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ai_numbers(self) -> list[ShownNumber]:
        return [n for n in self.numbers if n.surface == "ai_overview"]

    def ai_address_matches(self, office: Office) -> bool | None:
        """Does the AI Overview's address carry the office's official PIN? None if it gives none."""
        if not self.ai_pincodes or not office.pincode:
            return None
        return office.pincode in self.ai_pincodes

    def mode_address_matches(self, office: Office) -> bool | None:
        """The same check for AI Mode's answer."""
        if not self.mode_pincodes or not office.pincode:
            return None
        return office.pincode in self.mode_pincodes


def search_name(office: Office) -> str:
    """The office's name as a citizen would type it: no bracketed area ("RTO Bengaluru South"), and
    the office type when the name is only a place ("Sub Registrar Office Basavanagudi")."""
    prefix = OFFICE_TYPES[office.office_type].search_prefix if office.office_type in OFFICE_TYPES else ""
    return prefix + re.sub(r"\s*\([^)]*\)", "", office.name).strip()


def search_params(office: Office, city: City) -> dict[str, Any]:
    return {"engine": "google", "q": f"{search_name(office)} phone number", "location": city.location, **INDIA}


def ai_mode_params(office: Office, city: City) -> dict[str, Any]:
    """The same question in Google's AI Mode (it takes no google_domain)."""
    return {"engine": "google_ai_mode", "q": f"{search_name(office)} phone number", "location": city.location,
            "hl": INDIA["hl"], "gl": INDIA["gl"]}


def _flatten(blocks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in blocks:
        if block.get("snippet"):
            parts.append(block["snippet"])
        for item in block.get("list", []):
            parts.append(item.get("snippet", ""))
            parts.extend(_flatten(item.get("list", [])).splitlines())
        if block.get("rows"):
            parts.extend(" | ".join(str(c) for c in row) for row in block["rows"])
    return "\n".join(p for p in parts if p)


def classify(phone: phones.Phone, office: Office, data: OfficialData) -> tuple[Verdict, str]:
    if phone.key in office.phone_keys:
        return "this office", "in the official directory for this office"
    other = next((o for o in data.offices.values() if phone.key in o.phone_keys), None)
    if other and other.kind == "RPO" and office.office_type == other.office_type and office.kind != "RPO":
        return "regional office", f"the official number of {other.name}, which runs this centre"
    if other:
        return "another office", f"the official number of {other.code or other.name}"
    if phone.key in data.national:
        return "national helpline", data.national[phone.key].name
    if any(phone.key == h.key for h in data.helplines.values()):
        return "department helpline", "a department-wide helpline"
    return "not in the directory", "not in the official directory"


def _domain(link: str) -> str:
    return re.sub(r"^https?://(?:www\.)?([^/]+).*$", r"\1", link or "")


def citizen_view(client: SearchClient, office: Office, data: OfficialData, city: City) -> CitizenView:
    params = search_params(office, city)
    view = CitizenView(office.id, params["q"])
    try:
        result = client.search(params)
    except (CacheMiss, BudgetExceeded, SearchError) as e:
        view.notes.append(str(e))
        return view
    meta = result.get("search_metadata", {})
    view.search_id, view.google_url = meta.get("id", ""), meta.get("google_url", "")
    view.searched_on = (meta.get("created_at") or "")[:10]

    def add(text: str, surface: Surface, source: str) -> None:
        for phone in phones.find_all(text or ""):
            if all(n.phone.key != phone.key or n.surface != surface for n in view.numbers):
                verdict, detail = classify(phone, office, data)
                view.numbers.append(ShownNumber(phone, surface, source, verdict, detail))

    overview = result.get("ai_overview") or {}
    if overview.get("page_token") and not overview.get("text_blocks"):
        view.ai_followup = True
        try:
            overview = client.search({"engine": "google_ai_overview", "page_token": overview["page_token"]}).get("ai_overview") or {}
        except (CacheMiss, BudgetExceeded, SearchError) as e:
            view.notes.append(f"AI Overview not fetched: {e}")
            overview = {}
    if overview.get("text_blocks"):
        view.ai_text = _flatten(overview["text_blocks"])
        view.ai_references = [(r.get("title", ""), r.get("link", "")) for r in overview.get("references", [])]
        view.ai_pincodes = ["".join(m) for m in _PINCODE.findall(view.ai_text)]
        add(view.ai_text, "ai_overview", "AI Overview")

    graph = result.get("knowledge_graph") or {}
    add(graph.get("phone", ""), "knowledge_graph", graph.get("title", "knowledge panel"))
    local = result.get("local_results") or {}
    for place in (local.get("places", []) if isinstance(local, dict) else local):
        add(place.get("phone", ""), "local_pack", place.get("title", ""))
    for organic in result.get("organic_results", []):
        add(f"{organic.get('title', '')} {organic.get('snippet', '')}", "snippet", _domain(organic.get("link", "")))

    try:
        mode = client.search(ai_mode_params(office, city))
    except (CacheMiss, BudgetExceeded, SearchError) as e:
        view.notes.append(f"AI Mode not fetched: {e}")
        return view
    if mode.get("text_blocks"):
        mode_meta = mode.get("search_metadata", {})
        view.mode_search_id, view.mode_searched_on = mode_meta.get("id", ""), (mode_meta.get("created_at") or "")[:10]
        view.mode_text = _flatten(mode["text_blocks"])
        view.mode_references = [(r.get("title", ""), r.get("link", "")) for r in mode.get("references", [])]
        view.mode_pincodes = ["".join(m) for m in _PINCODE.findall(view.mode_text)]
        add(view.mode_text, "ai_mode", "AI Mode")
    return view


def to_dict(view: CitizenView, office: Office) -> dict[str, Any]:
    return {
        **{k: v for k, v in asdict(view).items() if k != "numbers"},
        "ai_address_matches": view.ai_address_matches(office),
        "mode_address_matches": view.mode_address_matches(office),
        "numbers": [{"phone": n.phone.key, "display": n.phone.display, "kind": n.phone.kind, "surface": n.surface,
                     "source": n.source, "verdict": n.verdict, "detail": n.detail} for n in view.numbers],
    }


def save(views: list[tuple[CitizenView, Office]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([to_dict(v, o) for v, o in views], ensure_ascii=False, indent=1), encoding="utf-8")
    return path
