"""Build the display snapshot: everything the web app, the MCP server and the README show.

A snapshot joins the official data, the saved collection, the scores and the citizen view
into one JSON file per city and office type (data/snapshot/). It holds no reviewer names and
no raw API responses, only masked quotes with links, so it can be committed: the demo runs
from it with no API key. Every headline number is computed here, never typed in by hand.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Final

from collections import Counter
from functools import lru_cache

from . import citizen, crosscheck, lookup, models, phones
from .client import CACHE_DIR, SearchClient
from .collect import COLLECTED_DIR
from .offices import CITIES as CITIES_BY_NAME, OFFICE_TYPES, place_names
from .official import Office, OfficialData
from .paths import DATA_DIR
from .redact import local_names, mask_emails, mask_listed, mask_phones, safe_quote, source_title
from .score import BREACH_MARGIN, ISSUE_WINDOW_DAYS, MIN_SAMPLE, RECENT_DAYS, Breach, OfficeScore, score_collection

SNAPSHOT_DIR: Final = DATA_DIR / "snapshot"


def _breach(b: Breach) -> dict[str, Any]:
    return {"service": b.service.name, "service_id": b.service.id, "statutory_days": b.service.days, "unit": b.service.unit,
            "citation": b.service.citation, "reported_days": b.reported_days, "reported_working_days": b.reported_working_days,
            "said": b.said, "explanation": b.explanation, "quote": asdict(b.quote)}


def official_keys(data: OfficialData) -> frozenset[str]:
    """Phone keys that may be published in full: offices' directory numbers and helplines."""
    return frozenset(k for o in data.offices.values() for k in o.phone_keys) | frozenset(data.national) \
        | frozenset(h.key for h in data.helplines.values())


def _shown(phone: phones.Phone, verdict: str) -> str:
    """How to display a number Google shows: in full if it's an office's or a helpline, else a mobile is masked."""
    return phone.display if verdict != "not in the directory" else phone.masked


def _bing(row: dict[str, Any], keep: frozenset[str]) -> models.BingCheck:
    """The office on Bing Maps, if a place there was taken to be it. A number not in the directory is masked."""
    phone = phones.Phone(row["phone"], row["phone_kind"]) if row["phone"] else None
    keep = keep | frozenset(w.upper() for w in keep)  # Bing writes some titles in capitals ("RTO ANJANAPURA KA 05")
    return {"found": bool(row["title"]), "title": safe_quote(row["title"], keep), "how": row["how"], "search_id": row["search_id"],
            "query": row["query"], "phone_display": _shown(phone, row["verdict"]) if phone else "", "phone_verdict": row["verdict"]}


def _lookalikes(unmatched: list[dict[str, Any]], kind: Any, keep: frozenset[str]) -> list[dict[str, Any]]:
    """Listings in the city named like the government office that aren't among the official offices. They may be
    agents or anything else; their phone numbers aren't republished."""
    if not kind.official_name:
        return []
    seen, out = set(), []
    for u in unmatched:
        pin = (re.findall(r"(?<!\d)(560\d{3})(?!\d)", u.get("address", "")) or [""])[-1]
        if pin and kind.official_name.search(u["title"]) and not kind.facility.search(u["title"]) and (u["title"], pin) not in seen:
            seen.add((u["title"], pin))
            out.append({"title": safe_quote(u["title"], keep), "category": u.get("category", ""), "pincode": pin,
                        "reviews": u.get("reviews", 0),
                        "lat": round(u["lat"], 4) if u.get("lat") is not None else None,
                        "lng": round(u["lng"], 4) if u.get("lng") is not None else None})
    return out


def _maps_url(listing: dict[str, Any]) -> str:
    return f"https://www.google.com/maps/place/?q=place_id:{listing['place_id']}" if listing.get("place_id") else ""


def display_name(office: Office) -> str:
    """'RTO Bengaluru South (Anjanapura)' as is; a bare place name gets its office type: 'Malleshwaram Sub-Registrar Office'."""
    suffix = OFFICE_TYPES[office.office_type].name_suffix if office.office_type in OFFICE_TYPES else ""
    return office.name if not suffix or "office" in office.name.lower() else office.name + suffix


def _office(score: OfficeScore, evidence: dict[str, Any], view: dict[str, Any] | None, data: OfficialData,
            keep: frozenset[str]) -> models.Office:
    office = score.office
    listing = dict(score.listing) if score.listing else None
    listing_key = ""
    if listing:
        # Listing titles are written by anyone on Google, and some name a person. The raw phone is
        # dropped: only the checked phone_display, masked when it may be private, is published.
        listing["title"] = safe_quote(listing["title"], keep)
        listing["maps_url"] = _maps_url(listing)
        listing.pop("phone", None)
        shown = phones.parse(listing.pop("phone_raw", ""))
        listing_key = shown.key if shown else ""
        if shown:
            verdict, detail = citizen.classify(shown, office, data)
            listing |= {"phone_display": _shown(shown, verdict), "phone_verdict": verdict, "phone_detail": detail}
    others = []
    for other in evidence.get("listings", []):
        if other["data_id"] == evidence.get("primary_id"):
            continue
        phone = phones.parse(other.get("phone_raw", ""))
        # A private business's number isn't ours to republish; an office's or a helpline's is shown.
        display = "" if not phone or other["match"]["role"] == "private" else _shown(phone, citizen.classify(phone, office, data)[0])
        others.append({"title": safe_quote(other["title"], keep), "role": other["match"]["role"], "reviews": other["reviews"],
                       "unclaimed": other["unclaimed"], "phone_display": display, "maps_url": _maps_url(other),
                       "reasons": other["match"]["reasons"]})
    if view:
        # Only directory and helpline numbers are published in full. Anything else Google shows may be
        # a private mobile: masked in the text, the reference titles and the number list alike.
        official = official_keys(data)
        first = next((n for n in view["numbers"] if n["surface"] == "ai_overview"), None)
        repeats = bool(first and listing_key and first["phone"] == listing_key)
        # Google's AI text can name an officer ("Senior Sub Registrar: <name>"): names found by reading are masked.
        # Unverified email addresses are masked too, and a cited social media post is named by its site only.
        emails = frozenset(o.email.lower() for o in data.offices.values() if o.email)

        def clean(text: str) -> str:
            return mask_emails(mask_phones(mask_listed(text, local_names()), official), emails)

        # Verdicts are worked out again from today's directory, so a rule added since the search was saved applies.
        def judged(n: dict[str, Any]) -> dict[str, Any]:
            verdict, detail = citizen.classify(phones.Phone(n["phone"], n["kind"]), office, data)
            return n | {"verdict": verdict, "detail": detail}
        view = {**view, "ai_text": clean(view.get("ai_text", "")),
                "ai_references": [[clean(source_title(title, link)), link] for title, link in view["ai_references"]],
                "mode_text": clean(view.get("mode_text", "")),
                "mode_references": [[clean(source_title(title, link)), link] for title, link in view.get("mode_references", [])],
                "numbers": [judged(n) if n["phone"] in official else
                            judged(n) | {"display": phones.Phone(n["phone"], n["kind"]).masked, "phone": ""} for n in view["numbers"]]}
    ai = None
    if view and view.get("ai_text"):
        first = next((n for n in view["numbers"] if n["surface"] == "ai_overview"), None)
        ai = {"text": view["ai_text"], "first_number": first, "searched_on": view.get("searched_on", ""), "numbers": [n for n in view["numbers"] if n["surface"] == "ai_overview"],
              "pincodes": view["ai_pincodes"], "address_matches": view["ai_address_matches"],
              "references": view["ai_references"], "search_id": view["search_id"], "query": view["query"],
              "repeats_listing_number": repeats}
    mode = None
    if view and view.get("mode_text"):
        numbers = [n for n in view["numbers"] if n["surface"] == "ai_mode"]
        mode = {"text": view["mode_text"], "first_number": numbers[0] if numbers else None, "searched_on": view.get("mode_searched_on", ""),
                "numbers": numbers, "pincodes": view.get("mode_pincodes", []), "address_matches": view.get("mode_address_matches"),
                "references": view["mode_references"], "search_id": view.get("mode_search_id", "")}
    return {
        "id": office.id, "code": office.code, "name": office.name, "display_name": display_name(office),
        "office_type": office.office_type, "aliases": list(office.aliases), "kind": office.kind, "address": office.address,
        "pincode": office.pincode, "email": office.email, "source_url": office.source_url, "notes": list(office.notes),
        "official_phones": [{"display": p.phone.display, "label": p.label, "tel": p.phone.key} for p in office.phones],
        "listing": listing,
        "other_listings": others,
        "reach": {"score": score.reachability.score, "basis": score.reachability.basis,
                  "checks": [asdict(c) | {"points": c.points} for c in score.reachability.checks]},
        "sample_size": score.sample_size, "window_reviews": score.window_reviews, "span": score.span,
        "enough_evidence": score.enough_evidence, "problem_reviews": score.problem_reviews, "positive_reviews": score.positive_reviews,
        "sampled": score.sampled, "searched_individually": evidence.get("searched_individually", True),
        "citizen_checked": view is not None,
        "issues": [asdict(i) for i in score.issues],
        "breaches": [_breach(b) for b in score.breaches],
        "agent_waits": [_breach(b) for b in score.agent_waits],
        "older_breaches": score.older_breaches,
        "ai_overview": ai,
        "ai_mode": mode,
        "citizen_search": {"query": view["query"], "search_id": view["search_id"],
                           "numbers": [n for n in view["numbers"] if n["surface"] not in ("ai_overview", "ai_mode")]} if view else None,
    }


def _headline(offices: list[models.Office], listing_keys: dict[str, str]) -> models.Headline:
    """`listing_keys`: office id -> the full phone number on its primary listing (never published)."""
    listed = [o for o in offices if o["listing"]]
    with_ai = [o for o in offices if o["ai_overview"]]
    with_mode = [o for o in offices if o["ai_mode"]]
    shown = [o for o in listed if o["listing"].get("phone_display")]
    # The same number (compared in full, not as masked) on the primary listings of different offices. Only numbers
    # outside the directory count: a national helpline on several listings is shared by design.
    shown_unknown = [o for o in shown if o["listing"].get("phone_verdict") == "not in the directory"]
    by_number = Counter(listing_keys[o["id"]] for o in shown_unknown)
    shared = [{"display": group[0]["listing"]["phone_display"], "offices": [o["display_name"] for o in group],
               "names": [o["code"] or o["name"] for o in group]}
              for key, count in by_number.items() if count > 1
              for group in [[o for o in shown_unknown if listing_keys[o["id"]] == key]]]
    return {
        "offices": len(offices),
        "official_phone": sum(bool(o["official_phones"]) for o in offices),
        "official_landline": sum(any(p["label"] == "landline" for p in o["official_phones"]) for o in offices),
        "listed": len(listed),
        "not_found": [o["code"] or o["display_name"] for o in offices if not o["listing"]],
        "listing_no_phone": sum(not o["listing"].get("phone_display") for o in listed),
        "listing_official_phone": sum(o["listing"].get("phone_verdict") == "this office" for o in listed),
        "listing_phone_shown": len(shown),
        "listing_phone_not_in_directory": sum(o["listing"].get("phone_verdict") == "not in the directory" for o in shown),
        "shared_listing_numbers": shared,
        "listing_unclaimed": sum(bool(o["listing"].get("unclaimed")) for o in listed),
        "ai_overviews": len(with_ai),
        "ai_first_number_right": sum((o["ai_overview"]["first_number"] or {}).get("verdict") == "this office" for o in with_ai),
        "ai_address_wrong": [o["code"] or o["display_name"] for o in with_ai if o["ai_overview"]["address_matches"] is False],
        "ai_first_number_from_listing": sum(o["ai_overview"]["repeats_listing_number"] for o in with_ai),
        "bing_checked": sum(o["bing"] is not None for o in offices),
        "bing_found": sum(bool(o["bing"] and o["bing"]["found"]) for o in offices),
        "bing_no_phone": sum(bool(o["bing"] and o["bing"]["found"] and not o["bing"]["phone_display"]) for o in offices),
        "bing_official_phone": sum(bool(o["bing"] and o["bing"]["phone_verdict"] == "this office") for o in offices),
        "ai_mode_answers": len(with_mode),
        "ai_mode_first_number_right": sum((o["ai_mode"]["first_number"] or {}).get("verdict") == "this office" for o in with_mode),
        "ai_mode_address_wrong": [o["code"] or o["display_name"] for o in with_mode if o["ai_mode"]["address_matches"] is False],
        "citizen_checked": sum(o["citizen_checked"] for o in offices),
        "sampled": sum(o["sampled"] and bool(o["listing"]) for o in offices),
        "recent_breaches": sum(len(o["breaches"]) for o in offices),
        "enough_evidence": sum(o["enough_evidence"] for o in offices),
    }


def _searched_at(params: dict[str, Any]) -> str:
    """When SerpApi ran a search ("2026-10-08 02:38 UTC"), from its cached response; "" if not cached here."""
    path = CACHE_DIR / f"{params.get('engine', 'google')}-{SearchClient.cache_key(params)}.json"
    try:
        created = json.loads(path.read_text(encoding="utf-8")).get("search_metadata", {}).get("created_at", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""
    return created[:16] + " UTC" if created else ""


def _step(engine: str, purpose: str, params: dict[str, Any], search_id: str) -> dict[str, str]:
    return {"engine": engine, "purpose": purpose, "search_id": search_id, "searched_at": _searched_at(params)}


def _trail(office: Office, evidence: dict[str, Any], searches: list[dict[str, Any]], view: dict[str, Any] | None,
           sweep_queries: tuple[str, ...]) -> list[dict[str, str]]:
    """Every SerpApi search behind one office, in the order they ran (the city-wide Maps sweep is listed
    once per office type, not here)."""
    listings = {l["data_id"]: l for l in evidence.get("listings", [])}
    steps = []
    for s in searches:
        engine, params = s["engine"], s["params"]
        if engine == "google_maps" and params.get("q") not in sweep_queries and office.name in params.get("q", ""):
            steps.append(_step(engine, f'Maps search for this office: "{params["q"]}"', params, s["search_id"]))
        elif engine == "google_maps_reviews" and params.get("data_id") in listings:
            which = "its listing" if params["data_id"] == evidence.get("primary_id") else "another of its listings"
            what = (f'reviews of {which} mentioning "{params["query"]}"' if params.get("query")
                    else f"newest reviews of {which}" + (", next page" if params.get("next_page_token") else ""))
            steps.append(_step(engine, what[0].upper() + what[1:], params, s["search_id"]))
    if view:
        params = citizen.search_params(office, CITIES_BY_NAME[evidence.get("city", "Bengaluru")])
        steps.append(_step("google", f'Google Search, as a citizen: "{view["query"]}"', params, view["search_id"]))
        if view.get("ai_followup"):
            token = _ai_page_token(params)
            if token:
                ai_params = {"engine": "google_ai_overview", "page_token": token}
                steps.append(_step("google_ai_overview", "Google's AI Overview for that search", ai_params,
                                   _cached_id(ai_params)))
        if view.get("mode_search_id"):
            mode_params = citizen.ai_mode_params(office, CITIES_BY_NAME[evidence.get("city", "Bengaluru")])
            steps.append(_step("google_ai_mode", "The same question in Google's AI Mode", mode_params, view["mode_search_id"]))
    return steps


def _ai_page_token(params: dict[str, Any]) -> str:
    path = CACHE_DIR / f"google-{SearchClient.cache_key(params)}.json"
    try:
        return (json.loads(path.read_text(encoding="utf-8")).get("ai_overview") or {}).get("page_token", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


def _cached_id(params: dict[str, Any]) -> str:
    path = CACHE_DIR / f"{params.get('engine', 'google')}-{SearchClient.cache_key(params)}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("search_metadata", {}).get("id", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


def _listing_key(score: OfficeScore) -> str:
    phone = phones.parse((score.listing or {}).get("phone_raw", ""))
    return phone.key if phone else ""


@lru_cache(maxsize=1)
def _popular_times() -> dict[str, dict[str, Any]]:
    """Google's typical busyness by hour ("popular times"), from every saved response that has it, by search ID."""
    found: dict[str, dict[str, Any]] = {}
    for path in CACHE_DIR.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        if "popular_times" not in text:
            continue
        result = json.loads(text)
        place = result.get("knowledge_graph") or result.get("place_results") or {}
        if (place.get("popular_times") or {}).get("graph_results"):
            found[result["search_metadata"]["id"]] = {"engine": result["search_parameters"]["engine"], "place": place,
                                                      "place_id": result["search_parameters"].get("place_id", "")}
    return found


def _hour(label: str) -> int | None:
    m = re.match(r"(\d{1,2})\s*(am|pm)", label.replace("\u202f", " ").strip().lower())
    return None if not m else int(m[1]) % 12 + (12 if m[2] == "pm" else 0)


def _busy(o: dict[str, Any], office: Office) -> dict[str, Any] | None:
    """Google's typical busyness for the office, by weekday and hour, when a saved response shows it for this very
    place: the response came from one of the office's own searches, and its title or address names the office (or it
    is the office's own listing). The snapshot keeps the typical hours only, not that moment's "live" reading."""
    ids = {s["search_id"] for s in o["trail"]} | ({o["listing"]["search_id"]} if o["listing"] else set())
    words = {w for name in (office.name, *office.aliases) for w in lookup.tokens(name) if len(w) > 3}
    for search_id, hit in _popular_times().items():
        place = hit["place"]
        own_listing = bool(o["listing"]) and hit["place_id"] == o["listing"].get("place_id")
        named = bool(words & set(lookup.tokens(f"{place.get('title', '')} {place.get('address', '')}"))) or \
            (office.code and office.code.replace("-", " ").lower() in place.get("title", "").replace("-", " ").lower())
        if own_listing or (search_id in ids and named):
            days = {day: [[h, int(x.get("busyness_score") or 0)] for x in hours if (h := _hour(x.get("time", ""))) is not None]
                    for day, hours in place["popular_times"]["graph_results"].items()}
            return {"title": place.get("title", ""), "engine": hit["engine"], "search_id": search_id, "days": days}
    return None


def build(data: OfficialData, city: str, office_type: str) -> models.Snapshot:
    collection = json.loads((COLLECTED_DIR / f"{city.lower()}-{office_type}.json").read_text(encoding="utf-8"))
    citizen_path = COLLECTED_DIR / f"{city.lower()}-{office_type}-citizen.json"
    views = {v["office_id"]: v for v in json.loads(citizen_path.read_text(encoding="utf-8"))} if citizen_path.exists() else {}
    scores = score_collection(collection, data)
    keep = frozenset(w for o in data.offices_of(office_type) for p in place_names(o) for w in p.split())
    offices = [_office(s, collection["offices"][s.office.id], views.get(s.office.id), data, keep) for s in scores]
    bing_path = COLLECTED_DIR / f"{city.lower()}-{office_type}-bing.json"
    bing = {b["office_id"]: b for b in json.loads(bing_path.read_text(encoding="utf-8"))} if bing_path.exists() else {}
    for o in offices:
        o["bing"] = _bing(bing[o["id"]], keep) if o["id"] in bing else None
    sweep = OFFICE_TYPES[office_type].maps_queries
    for o, sc in zip(offices, scores):
        o["trail"] = _trail(sc.office, collection["offices"][sc.office.id] | {"city": city}, collection["searches"],
                            views.get(sc.office.id), sweep)
        if o["bing"] and o["bing"]["search_id"]:
            params = crosscheck.bing_params(sc.office, CITIES_BY_NAME[city])
            o["trail"].append(_step("bing_maps", f'Bing Maps, the same office: "{params["q"]}"', params, o["bing"]["search_id"]))
        o["busy"] = _busy(o, sc.office)
    kind = OFFICE_TYPES[office_type]
    # The searches behind this snapshot (each distinct request once, whether or not it was cached).
    engines: dict[str, int] = {}
    for s in collection["searches"]:
        engines[s["engine"]] = engines.get(s["engine"], 0) + 1
    if views:  # one Google search per office, plus the AI Overview where Google deferred it
        engines["google"] = len(views)
        engines["google_ai_overview"] = sum(bool(v.get("ai_followup")) for v in views.values())
        engines["google_ai_mode"] = sum(bool(v.get("mode_search_id")) for v in views.values())
    if bing:
        engines["bing_maps"] = len(bing)
    return {
        "city": city,
        "office_type": office_type,
        "profile": {"label": kind.label, "short": kind.short, "plural": kind.plural, "department": kind.department, "officer": kind.officer,
                    "review_queries": list(kind.review_queries), "promise": kind.promise, "promise_name": kind.promise_name,
                    "directory_url": offices[0]["source_url"] if offices else ""},
        "as_of": collection["collected_at"][:10],
        "rules": {"issue_window_days": ISSUE_WINDOW_DAYS, "min_sample": MIN_SAMPLE, "recent_days": RECENT_DAYS,
                  "breach_margin_pct": round((BREACH_MARGIN - 1) * 100)},
        "headline": _headline(offices, {s.office.id: _listing_key(s) for s in scores}),
        "offices": offices,
        "timelines": [asdict(t) | {"citation": t.citation, "limit": t.limit} for t in data.timelines_for(office_type)],
        "appeals": asdict(data.appeals[office_type]) if office_type in data.appeals else None,
        "helpline": data.helplines[office_type].display if office_type in data.helplines else "",
        "grievance": data.grievances.get(office_type),
        "unmatched": [{"title": safe_quote(u["title"], keep), "why": u["why"]} for u in collection["unmatched"]],
        "lookalikes": _lookalikes(collection["unmatched"], kind, keep),
        "sweep": [_step(x["engine"], f'Maps sweep: "{x["params"]["q"]}"' + (f', page {x["params"]["start"] // 20 + 1}'
                                                                                  if x["params"].get("start") else ""),
                        x["params"], x["search_id"])
                  for x in collection["searches"] if x["engine"] == "google_maps" and x["params"].get("q") in sweep],
        "searches_by_engine": engines,
        "searches": sum(engines.values()),
    }


def save(snapshot: models.Snapshot) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"{snapshot['city'].lower()}-{snapshot['office_type']}.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def load(city: str, office_type: str) -> models.Snapshot:
    return json.loads((SNAPSHOT_DIR / f"{city.lower()}-{office_type}.json").read_text(encoding="utf-8"))
