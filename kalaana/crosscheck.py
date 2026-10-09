"""Is it only Google? Each office looked up on Bing Maps (SerpApi's bing_maps engine).

One Bing Maps search per office, by the name a citizen would type, centred on the city. A Bing
place counts as the office when it sits within MATCH_METRES of the office's Google Maps listing
and looks like this office type, or (when Google has no listing) when its title names the office's
place and looks like this office type. Its phone, if any, is checked against the directory.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from . import phones
from .citizen import Verdict, classify, search_name
from .client import BudgetExceeded, CacheMiss, SearchClient, SearchError
from .offices import OFFICE_TYPES, City, place_names
from .official import Office, OfficialData

MATCH_METRES: Final = 400


def bing_params(office: Office, city: City) -> dict[str, Any]:
    lat, lng = city.ll.lstrip("@").split(",")[:2]
    return {"engine": "bing_maps", "q": search_name(office), "cp": f"{lat}~{lng}"}


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    rad = math.pi / 180
    h = (math.sin((b[0] - a[0]) * rad / 2) ** 2
         + math.cos(a[0] * rad) * math.cos(b[0] * rad) * math.sin((b[1] - a[1]) * rad / 2) ** 2)
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def places(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Bing's places, flattened (SerpApi nests them in groups of `items`). When Bing is sure of one
    place it returns that alone, as `place_results`."""
    out: list[dict[str, Any]] = [result["place_results"]] if isinstance(result.get("place_results"), dict) else []
    for entry in result.get("local_results") or []:
        out.extend(entry.get("items", [entry]) if isinstance(entry, dict) else [])
    return [p for p in out if p.get("title")]


@dataclass
class BingLook:
    office_id: str
    query: str
    search_id: str = ""
    title: str = ""
    address: str = ""
    phone: phones.Phone | None = None
    verdict: Verdict | None = None
    detail: str = ""
    how: str = ""  # why this place was taken to be the office
    note: str = ""  # the search didn't run

    @property
    def found(self) -> bool:
        return bool(self.title)


def match(office: Office, candidates: list[dict[str, Any]], google_at: tuple[float, float] | None) -> tuple[dict[str, Any], str] | None:
    kind = OFFICE_TYPES[office.office_type]

    def looks_right(p: dict[str, Any]) -> bool:
        text = f"{p.get('title', '')} {p.get('type', '')}"
        return bool(kind.looks_like.search(text) or re.search(r"motor vehicles|government", p.get("type", ""), re.I)) \
            and not kind.private.search(p.get("title", "")) and not kind.not_an_office.search(p.get("title", ""))

    near = []
    for p in candidates:
        gps = p.get("gps_coordinates") or {}
        if google_at and "latitude" in gps and looks_right(p):
            d = metres(google_at, (gps["latitude"], gps["longitude"]))
            if d <= MATCH_METRES:
                near.append((d, p))
    if near:
        d, p = min(near, key=lambda x: x[0])
        return p, f"{round(d)} m from its Google Maps listing"
    for p in candidates:
        named = [n for n in place_names(office) if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", p.get("title", ""), re.I)]
        if named and looks_right(p):
            return p, f"title names {named[0]}"
    return None


def look(client: SearchClient, office: Office, data: OfficialData, city: City, google_at: tuple[float, float] | None) -> BingLook:
    params = bing_params(office, city)
    result = BingLook(office.id, params["q"])
    try:
        found = client.search(params)
    except (CacheMiss, BudgetExceeded, SearchError) as e:
        result.note = str(e)
        return result
    result.search_id = found.get("search_metadata", {}).get("id", "")
    hit = match(office, places(found), google_at)
    if hit:
        place, result.how = hit
        result.title, result.address = place.get("title", ""), place.get("address", "")
        result.phone = phones.parse(place.get("phone", ""))
        if result.phone:
            result.verdict, result.detail = classify(result.phone, office, data)
    return result


def google_location(collection: dict[str, Any], office_id: str) -> tuple[float, float] | None:
    """Where the office's primary Google Maps listing is, from a saved collection."""
    ev = collection.get("offices", {}).get(office_id, {})
    primary = next((l for l in ev.get("listings", []) if l["data_id"] == ev.get("primary_id")), None)
    if primary and primary.get("lat") is not None:
        return primary["lat"], primary["lng"]
    return None


def save(looks: list[BingLook], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"office_id": b.office_id, "query": b.query, "search_id": b.search_id, "title": b.title, "address": b.address,
             "phone": b.phone.key if b.phone else "", "phone_kind": b.phone.kind if b.phone else "",
             "verdict": b.verdict, "detail": b.detail, "how": b.how} for b in looks]
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return path
