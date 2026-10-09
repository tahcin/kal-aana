"""What the app shows, shaped from the committed snapshots (data/snapshot/).

Every status, sentence and count here is derived from snapshot fields; nothing is typed in by hand.
web.py serves these as JSON to the React app (frontend/). The complaint drafter is here too, so its
working-day arithmetic and its letter are tested in Python.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any, Final, Literal
from zoneinfo import ZoneInfo

from . import evaluate, refine, snapshot
from .offices import OFFICE_TYPES

CITY: Final = "Bengaluru"
IST: Final = ZoneInfo("Asia/Kolkata")
SAKALA_IN_FORCE: Final = date(2012, 4, 2)  # no application before the Act's services began can be under it


class NotFound(LookupError):
    """No such office, office type or snapshot."""


def today_in_india() -> date:
    return datetime.now(IST).date()


# Tests replace this to fix "today".
clock_today: Callable[[], date] = today_in_india


@lru_cache(maxsize=8)
def load(city: str, office_type: str) -> dict[str, Any]:
    try:
        return snapshot.load(city, office_type)
    except (FileNotFoundError, json.JSONDecodeError):
        raise NotFound(f"No usable snapshot for {city} {office_type}. Build it with: kalaana snapshot {office_type}") from None


def office_types() -> list[str]:
    """Office types with a snapshot for the city, in the order OFFICE_TYPES lists them."""
    return [t for t in OFFICE_TYPES if (snapshot.SNAPSHOT_DIR / f"{CITY.lower()}-{t}.json").exists()]


def find_office(office_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """(snapshot, office) for an office id, from whichever office type it belongs to."""
    for office_type in office_types():
        data = load(CITY, office_type)
        office = next((o for o in data["offices"] if o["id"] == office_id), None)
        if office is not None:
            return data, office
    raise NotFound(f"No office {office_id}")


def phone_forms(display: str) -> list[str]:
    """How a landline may be written in AI text: '080 2663 0989' -> '080-26630989', '+91-80-26630989'."""
    digits = re.sub(r"\D", "", display)
    if not digits.startswith("0") or len(digits) != 11:
        return [display]
    area, rest = digits[1:3], digits[3:]
    return [display, f"0{area}-{rest}", f"+91-{area}-{rest}", f"+91 {area} {rest}", digits]


def ai_marks(office: dict[str, Any]) -> list[str]:
    """Words to highlight in an AI Overview: the numbers it gives and its PIN codes."""
    ai = office.get("ai_overview") or {}
    return [form for n in ai.get("numbers", []) for form in phone_forms(n["display"])] + list(ai.get("pincodes", []))


def working_days_since(start: date, end: date) -> int:
    """Working days after `start` up to `end`, skipping Sundays and the 2nd and 4th Saturdays
    (Karnataka government holidays by rule). Public holidays are not skipped, so this is an upper bound."""
    days, day = 0, start
    while day < end:
        day += timedelta(days=1)
        nth_saturday = (day.day - 1) // 7 + 1
        if day.weekday() == 6 or (day.weekday() == 5 and nth_saturday in (2, 4)):
            continue
        days += 1
    return days


MapsStatus = Literal["no_listing", "no_phone", "official", "helpline", "other"]
AIStatus = Literal["own", "helpline", "other", "no_answer", "unchecked"]

MAPS_LABELS: Final[dict[str, str]] = {
    "no_phone": "No phone on Google Maps",
    "other": "A number that isn't in the directory",
    "official": "The office's own number",
    "helpline": "A helpline, not the office's own number",
    "no_listing": "No listing found",
}
AI_LABELS: Final[dict[str, str]] = {
    "own": "Leads with the office's own number",
    "helpline": "Leads with a helpline, not the office's number",
    "other": "Leads with a different number",
    "no_answer": "No AI answer, or no number",
    "unchecked": "Not checked",
}


def possessive(name: str) -> str:
    """"Transport Department's", "Ministry of External Affairs'"."""
    return name + ("'" if name.endswith("s") else "'s")


def terms(timeline: dict[str, Any], profile: dict[str, Any]) -> str:
    """When a time limit's clock runs, in words: Sakala's marriage limits start once the documents are in; every
    passport limit runs from complete documentation, and some exclude police verification."""
    charter = profile.get("promise", "the law") != "the law"
    parts = [timeline["condition"]] if timeline.get("condition") else (
        ["from the receipt of complete documentation"] if charter else [])
    if timeline.get("excludes"):
        parts.append(f"excluding the {timeline['excludes']}")
    return ", ".join(parts)


def allows(profile: dict[str, Any]) -> str:
    """How the product names a time limit's source: "the law allows" (Sakala), "the Citizen's Charter promises"."""
    promise = profile.get("promise", "the law")
    return "the law allows" if promise == "the law" else f"{promise} promises"


def everything() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """(snapshot, office) for every office of every type."""
    return [(data, o) for t in office_types() for data in [load(CITY, t)] for o in data["offices"]]


def label(o: dict[str, Any]) -> str:
    return f"{o['code']} {o['name']}" if o["code"] else o["display_name"]


def maps_status(o: dict[str, Any]) -> MapsStatus:
    listing = o["listing"]
    if not listing:
        return "no_listing"
    if not listing.get("phone_display"):
        return "no_phone"
    if listing.get("phone_verdict") in ("national helpline", "department helpline"):
        return "helpline"
    return "official" if listing.get("phone_verdict") == "this office" else "other"


def ai_status(o: dict[str, Any]) -> AIStatus:
    if not o["citizen_checked"]:
        return "unchecked"
    first = (o["ai_overview"] or {}).get("first_number")
    if not first:
        return "no_answer"
    return _first_status(first)


def review_search_id(o: dict[str, Any], sample: str) -> str | None:
    """The Maps Reviews search a quote came from, when its sample names exactly one search."""
    if not sample.startswith("query:"):
        return None  # the newest-first sample spans several pages
    term = sample.removeprefix("query:")
    ids = [s["search_id"] for s in o["trail"] if s["engine"] == "google_maps_reviews" and f'"{term}"' in s["purpose"]]
    return ids[0] if len(ids) == 1 else None


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def further_down(o: dict[str, Any]) -> dict[str, Any] | None:
    """Official numbers that only other websites list, further down the search results (not the AI, panels or Maps)."""
    if not o["citizen_checked"]:
        return None
    snippets = [n for n in (o["citizen_search"] or {}).get("numbers", []) if n["surface"] == "snippet"]
    own = [n for n in snippets if n["verdict"] == "this office"]
    return {"numbers": len({n["display"] for n in snippets}), "own": sorted({n["display"] for n in own}),
            "sites": sorted({n["source"] for n in own})}


def takeaways(o: dict[str, Any], data: dict[str, Any], found: list[dict[str, Any]], k: dict[str, Any]) -> dict[str, str]:
    """One plain sentence per story step: what the step means for a citizen. Each is a fact from the snapshot."""
    listing, ai = o["listing"], o["ai_overview"]
    if not o["citizen_checked"]:
        search = "So the rest of this office's story comes from Google Maps alone."
    elif not ai:
        search = "So Google gave no AI Overview, and the citizen was left with the search results."
    elif not ai.get("first_number"):
        search = "So a citizen who asked got no number in Google's AI Overview."
    elif ai["first_number"]["verdict"] == "this office":
        search = ("So a citizen who searches gets the right number, but an address with a different PIN from the directory's."
                  if ai["address_matches"] is False else "So here Google's AI Overview gets it right: it leads with the office's own number.")
    elif ai["first_number"]["verdict"] == "regional office":
        search = "So a citizen who searches is given the regional passport office's line, not this centre's."
    elif ai["first_number"]["verdict"] == "another office":
        search = "So a citizen who searches is handed another office's number."
    elif ai["first_number"]["verdict"] == "not in the directory":
        search = "So a citizen who searches is handed a number that isn't in the department's directory."
    else:
        search = "So a citizen who searches is sent to a helpline queue, not to the office."
    mode = o.get("ai_mode")
    if o["citizen_checked"] and mode:
        mode_own = (mode["first_number"] or {}).get("verdict") == "this office"
        overview_ok = bool(ai and (ai.get("first_number") or {}).get("verdict") == "this office" and ai["address_matches"] is not False)
        if mode_own and not overview_ok:
            search += " Google's AI Mode, asked the same thing, leads with the office's own number" + \
                (" and PIN." if mode["address_matches"] else ".")
        elif not mode_own and overview_ok:
            search += " Google's AI Mode, asked the same thing, doesn't."

    shared = any(o["display_name"] in s["offices"] for s in data["headline"]["shared_listing_numbers"])
    if not listing:
        maps = "So a citizen looking on Google Maps may not find this office at all."
    elif not listing.get("phone_display"):
        maps = (f"So the office's own Google listing, with {listing['reviews']:,} reviews, shows no phone number."
                if listing.get("reviews") else "So the office's own Google listing shows no phone number.")
    elif listing.get("phone_verdict") == "this office":
        maps = "So here the listing shows the number the department publishes."
    elif listing.get("phone_verdict") in ("national helpline", "department helpline"):
        maps = "So the listing sends callers to a helpline queue, not to the office."
    elif shared:
        maps = "So the listing shows a number that isn't in the department's directory, and another office's listing shows the same one."
    else:
        maps = "So the listing shows a number that isn't in the department's directory."
    bing = o.get("bing")
    if bing and bing["found"]:
        if not bing["phone_display"]:
            maps += " Bing Maps shows no phone either." if listing and not listing.get("phone_display") else " Bing Maps shows no phone."
        elif bing["phone_verdict"] == "this office":
            maps += " Bing Maps does show the office's own number."
        else:
            maps += {"another office": " Bing Maps shows another office's number.",
                     "regional office": " Bing Maps shows the regional passport office's number.",
                     "not in the directory": " Bing Maps shows a number that isn't in the department's directory."
                     }.get(bing["phone_verdict"], " Bing Maps shows a helpline number, not the office's.")

    published, right = len(o["official_phones"]), sum(f["verdict"] == "this office" for f in found)
    theirs = "the one number the department publishes" if published == 1 else f"the {published} numbers the department publishes"
    up_front = "Google's AI answer, its panels or the Maps listing" if o["citizen_checked"] else "the Maps listing"
    shown = "Google showed up front" if o["citizen_checked"] else "on the Maps listing"
    if not found and not o["citizen_checked"] and not listing:
        check = f"So there was nothing on Google to check against {theirs}."
    elif not found:
        check = (f"So the one number the department publishes is nowhere in {up_front}." if published == 1
                 else f"So none of the {published} numbers the department publishes is in {up_front}.")
    elif len(found) == 1:
        check = (f"So the one number {shown} is the office's own." if right else f"So the one number {shown} isn't the office's own.") \
            + f" The department publishes {published}."
    elif right:
        check = f"So of the {len(found)} numbers {shown}, {right} {'is' if right == 1 else 'are'} the office's own. The department publishes {published}."
    else:
        check = f"So none of the {len(found)} numbers {shown} is the office's own. The department publishes {published}."
    extra = [n for n in (further_down(o) or {}).get("own", []) if n not in {f["display"] for f in found}]
    if extra:
        count = ("one" if len(extra) == 1 else str(len(extra))) + (" more" if right else "")
        check += f" Further down the results, other websites list {count} of the department's numbers."

    if k["reported_days"]:
        name = k["service"]
        service = "a " + name.removeprefix("Issue of ") if name.startswith("Issue of ") else "the " + name[0].lower() + name[1:]
        clock_line = (f"So one reviewer reports waiting about {k['reported_days']} working days for {service}, "
                      f"which {data['profile'].get('promise', 'the law')} promises in {k['limit']}.")
    elif o["sampled"] and o["agent_waits"]:
        clock_line = "So in the recent reviews we read, the waits past the limit were through an agent."
    elif o["sampled"] and o["older_breaches"]:
        clock_line = "So the recent reviews we read don't report a wait past the limit; older reviews do."
    elif o["sampled"]:
        clock_line = "So for this office, the recent reviews we read don't show the deadline broken."
    else:
        clock_line = "So we can't say how long this office really takes."
    return {"search": search, "maps": maps, "check": check, "clock": clock_line}


def clock(o: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """The promise clock: a reviewer's reported wait against the legal limit, or the limit alone."""
    if o["breaches"]:
        b = o["breaches"][0]
        return {"service": b["service"], "limit_days": b["statutory_days"], "limit": f"{b['statutory_days']} {b['unit']}",
                "reported_days": b["reported_working_days"], "said": b["said"], "date": b["quote"]["date"],
                "rating": b["quote"]["rating"],
                "conversion": f'The reviewer wrote "{b["said"]}". At five working days a week, that is about '
                              f'{b["reported_working_days"]} working days.',
                "link": b["quote"]["link"], "citation": b["citation"], "quote": b["quote"]["text"], "evidence": b["quote"]["evidence"],
                "search_id": review_search_id(o, b["quote"]["sample"])}
    t = data["timelines"][0]
    years = data["rules"]["recent_days"] // 365
    if not o["sampled"]:
        note = "This office's reviews weren't sampled, so we can't say how long it actually takes."
    elif o["agent_waits"] or o["older_breaches"]:
        note = (f"No review from the last {years} years reports a wait past this limit"
                + (", apart from waits through an agent" if o["agent_waits"] else "")
                + (". Older reviews do." if o["older_breaches"] else "."))
    else:
        note = "No review we read for this office reports a wait past this limit."
    return {"service": t["name"], "limit_days": t["days"], "limit": t["limit"], "reported_days": None, "citation": t["citation"],
            "note": note, "terms": terms(t, data["profile"])}


def verdict(o: dict[str, Any], data: dict[str, Any]) -> list[str]:
    """Plain sentences, each one a fact from the snapshot, for the top of an office page."""
    out, listing, ai = [], o["listing"], o["ai_overview"]
    if not listing:
        out.append("Our searches found no Google Maps listing of its own.")
    elif not listing.get("phone_display"):
        out.append("Its Google Maps listing shows no phone number.")
    elif listing.get("phone_verdict") == "this office":
        out.append("Its Google Maps listing shows the office's own number.")
    elif listing.get("phone_verdict") in ("national helpline", "department helpline"):
        out.append(f"Its Google Maps listing shows a helpline ({listing['phone_display']}), not the office's own number.")
    else:
        out.append("Its Google Maps listing shows a number that isn't in the department's directory.")
    if listing and listing.get("unclaimed"):
        out[-1] = out[-1][:-1] + ", and Google marks it unclaimed: no verified owner manages it."
    for shared in data["headline"]["shared_listing_numbers"]:  # one number on several offices' listings
        if o["display_name"] in shared["offices"]:
            others = " and ".join(n for n in shared["offices"] if n != o["display_name"])
            out.append(f"The same number is the phone on the Google Maps listing of {others}.")
    if ai:
        first = ai.get("first_number")
        if first and first["verdict"] == "this office":
            out.append("Google's AI Overview leads with the right number" +
                       (", but gives an address with a different PIN." if ai["address_matches"] is False else "."))
        elif first and first["verdict"] in ("national helpline", "department helpline"):
            out.append(f"Google's AI Overview leads with a helpline ({first['display']}), not the office's own number.")
        elif first:
            out.append("Google's AI Overview leads with a number that isn't this office's" +
                       {"another office": ": it's another office's.",
                        "regional office": ": it's the regional passport office's."}.get(first["verdict"], "."))
        else:
            out.append("Google's AI Overview gives no number.")
    if o["breaches"]:
        b = o["breaches"][0]
        service = b["service"].removeprefix("Issue of ")
        out.append(f'A reviewer writes "{b["quote"]["evidence"]}" ({service[0].lower() + service[1:]}: {allows(data["profile"])} '
                   f"{b['statutory_days']} {b['unit']}).")
    elif o["enough_evidence"] and o["problem_reviews"]:
        out.append(f"{o['problem_reviews']} of its {o['window_reviews']} recent reviews with text report a problem.")
    return out


def story_card(o: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """What the story page needs for one office."""
    listing, ai = o["listing"] or {}, o["ai_overview"]
    found = [{"display": n["display"], "where": "Google's AI Overview", "verdict": n["verdict"], "detail": n["detail"]}
             for n in (ai or {}).get("numbers", [])]
    for n in (o["citizen_search"] or {}).get("numbers", []):
        if n["surface"] in ("knowledge_graph", "local_pack") and all(f["display"] != n["display"] for f in found):
            found.append({"display": n["display"], "where": "Google's business panel" if n["surface"] == "knowledge_graph"
                          else "Google's map results", "verdict": n["verdict"], "detail": n["detail"]})
    if listing.get("phone_display") and all(f["display"] != listing["phone_display"] for f in found):
        found.append({"display": listing["phone_display"], "where": "Google Maps listing",
                      "verdict": listing["phone_verdict"], "detail": listing.get("phone_detail", "")})
    for shared in data["headline"]["shared_listing_numbers"]:  # the same number on another office's listing
        others = [name for name in shared["offices"] if name != o["display_name"]]
        for f in found:
            if f["display"] == shared["display"] and o["display_name"] in shared["offices"]:
                f["also"] = "The same number is the phone on the Google Maps listing of " + " and ".join(others)
    k = clock(o, data)
    overview_ids = [s["search_id"] for s in o["trail"] if s["engine"] == "google_ai_overview"]
    return {
        "id": o["id"], "label": label(o), "type": data["profile"]["short"], "department": data["profile"]["department"],
        "official": o["official_phones"], "email": o["email"], "source_url": o["source_url"],
        "maps": {"title": listing.get("title"), "rating": listing.get("rating"), "reviews": listing.get("reviews"),
                 "phone": listing.get("phone_display"), "unclaimed": listing.get("unclaimed"), "url": listing.get("maps_url"),
                 "search_id": listing.get("search_id")} if listing else None,
        "ai": {"query": ai["query"], "text": ai["text"], "marks": ai_marks(o),
               "good_marks": [form for n in ai["numbers"] if n["verdict"] == "this office" for form in phone_forms(n["display"])]
               + (list(ai["pincodes"]) if ai["address_matches"] else []),
               "searched_on": ai["searched_on"],
               "search_id": ai["search_id"], "overview_search_id": overview_ids[0] if overview_ids else None,
               "sources": [{"title": title, "domain": re.sub(r"^www\.", "", url.split("/")[2])}
                           for title, url in ai.get("references", []) if url.startswith("http")], "address_matches": ai["address_matches"], "pincodes": ai["pincodes"],
               "official_pin": o["pincode"]} if ai else None,
        "mode": {"text": mode["text"], "marks": [f for n in mode["numbers"] for f in phone_forms(n["display"])] + list(mode["pincodes"]),
                 "good_marks": [f for n in mode["numbers"] if n["verdict"] == "this office" for f in phone_forms(n["display"])]
                 + (list(mode["pincodes"]) if mode["address_matches"] else []),
                 "first_verdict": (mode["first_number"] or {}).get("verdict"), "first_display": (mode["first_number"] or {}).get("display"),
                 "address_matches": mode["address_matches"], "pincodes": mode["pincodes"], "search_id": mode["search_id"],
                 "sources": [{"title": t, "domain": re.sub(r"^www\.", "", u.split("/")[2])} for t, u in mode["references"] if u.startswith("http")]}
        if (mode := o.get("ai_mode")) else None,
        "bing": o.get("bing"),
        "promise": {"allows": allows(data["profile"]), "name": data["profile"].get("promise_name", ""),
                    "kind": "law" if data["profile"].get("promise", "the law") == "the law" else "charter"},
        "query": (o["citizen_search"] or {}).get("query"),
        "found": found,
        "clock": k,
        "takeaways": takeaways(o, data, found, k),
        "searches": ([{"engine": "google_maps", "purpose": "Google Maps search that found its listing", "search_id": listing["search_id"]}]
                     if listing.get("search_id") and all(s["search_id"] != listing["search_id"] for s in o["trail"]) else [])
        + [{key: s[key] for key in ("engine", "purpose", "search_id")} for s in o["trail"]],
        "further": further_down(o),
        "verdict": verdict(o, data),
        "checked": o["citizen_checked"],
        "sampled": o["sampled"],
        "listed": bool(o["listing"]),
    }


def mode_status(o: dict[str, Any]) -> AIStatus:
    """What Google's AI Mode led with, in the same terms as ai_status."""
    if not o["citizen_checked"]:
        return "unchecked"
    first = (o.get("ai_mode") or {}).get("first_number")
    if not first:
        return "no_answer"
    return _first_status(first)


def _first_status(first: dict[str, Any]) -> AIStatus:
    if first["verdict"] == "this office":
        return "own"
    return "helpline" if first["verdict"] in ("national helpline", "department helpline") else "other"


def bing_status(o: dict[str, Any]) -> str | None:
    """"own", "other", "no_phone", "not_found", or None when Bing wasn't checked."""
    bing = o.get("bing")
    if not bing:
        return None
    if not bing["found"]:
        return "not_found"
    if not bing["phone_display"]:
        return "no_phone"
    return "own" if bing["phone_verdict"] == "this office" else "other"


def km_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    rad = math.pi / 180
    h = math.sin((b[0] - a[0]) * rad / 2) ** 2 + math.cos(a[0] * rad) * math.cos(b[0] * rad) * math.sin((b[1] - a[1]) * rad / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def nearby_lookalikes(o: dict[str, Any], data: dict[str, Any], limit: int = 4) -> list[dict[str, Any]]:
    """Listings named like this office type that aren't an official office, nearest first (straight line)."""
    listing = o["listing"] or {}
    here = (listing["lat"], listing["lng"]) if listing.get("lat") is not None else None
    out = [{**x, "km": round(km_between(here, (x["lat"], x["lng"])), 1) if here and x.get("lat") is not None else None}
           for x in data.get("lookalikes", [])]
    return sorted(out, key=lambda x: (x["km"] is None, x["km"] or 0))[:limit]


def map_points() -> list[dict[str, Any]]:
    points = []
    for data, o in everything():
        listing = o["listing"] or {}
        points.append({"id": o["id"], "label": label(o), "type": data["office_type"], "type_label": data["profile"]["short"],
                       "lat": listing.get("lat"), "lng": listing.get("lng"), "status": maps_status(o), "ai": ai_status(o),
                       "phone": listing.get("phone_display", ""), "score": o["reach"]["score"],
                       "unclaimed": bool(listing.get("unclaimed")), "reviews": listing.get("reviews", 0),
                       "mode": mode_status(o), "bing": bing_status(o)})
    return points


def shared_links() -> list[dict[str, Any]]:
    """Pairs of offices whose Maps listings show the same number (from each snapshot's headline)."""
    links = []
    for t in office_types():
        data = load(CITY, t)
        by_name = {o["display_name"]: o for o in data["offices"]}
        for shared in data["headline"]["shared_listing_numbers"]:
            ids = [by_name[name]["id"] for name in shared["offices"] if name in by_name]
            links.append({"display": shared["display"], "ids": ids, "names": shared["names"]})
    return links


def totals() -> dict[str, Any]:
    heads = {t: load(CITY, t)["headline"] for t in office_types()}
    return {"offices": sum(h["offices"] for h in heads.values()), "listed": sum(h["listed"] for h in heads.values()),
            "no_phone": sum(h["listing_no_phone"] for h in heads.values()),
            "official": sum(h["listing_official_phone"] for h in heads.values()),
            "unclaimed": sum(h["listing_unclaimed"] for h in heads.values()),
            "ai": sum(h["ai_overviews"] for h in heads.values()),
            "citizen_checked": sum(h["citizen_checked"] for h in heads.values()),
            "ai_right": sum(h["ai_first_number_right"] for h in heads.values()),
            "ai_mode": sum(h.get("ai_mode_answers", 0) for h in heads.values()),
            "ai_mode_right": sum(h.get("ai_mode_first_number_right", 0) for h in heads.values()),
            "bing_found": sum(h.get("bing_found", 0) for h in heads.values()),
            "bing_no_phone": sum(h.get("bing_no_phone", 0) for h in heads.values()),
            "bing_official": sum(h.get("bing_official_phone", 0) for h in heads.values()),
            "searches": sum(load(CITY, t)["searches"] for t in office_types()),
            "as_of": max(load(CITY, t)["as_of"] for t in office_types())}


HOLIDAY_SLACK: Final = 3  # public holidays aren't subtracted, so a count this close past the limit may still be within it


def wait_status(elapsed: int | None, limit_days: int) -> str:
    """"within", "near" (just past the limit, by fewer working days than public holidays could explain) or "past"."""
    if elapsed is None or elapsed <= limit_days:
        return "within"
    return "near" if elapsed <= limit_days + HOLIDAY_SLACK else "past"


def wait_sentence(elapsed: int, limit: str, limit_days: int, condition: str = "", source: str = "the law allows") -> str:
    """One honest sentence about a wait, for the ask box and the story. `condition` is when the clock starts
    ("after the documents required under the Act and Rules are submitted")."""
    status = wait_status(elapsed, limit_days)
    excluded = re.search(r"excluding the (.+)$", condition)
    if excluded and status != "within":  # the count can't take out a period the promise leaves out
        return (f"About {elapsed} working days since you applied (public holidays not subtracted). "
                f"{source[0].upper() + source[1:]} {limit} {condition}. This count includes any {excluded[1]}, "
                "so it can't show whether the limit was missed.")
    return (f"About {elapsed} working days since you applied (public holidays not subtracted). {source[0].upper() + source[1:]} {limit}"
            + (f" {condition}" if condition else "")
            + {"within": ", so you're still within it.",
               "near": ": that's at or just past the limit, depending on public holidays in between.",
               "past": ": that's past the limit" + (", if everything required was submitted when you applied." if condition else ".")}[status])


def your_wait(data: dict[str, Any], service: str, applied: str) -> dict[str, Any] | None:
    """A visitor's own application, for the story's deadline step: the service's legal limit, and the working
    days since the date they gave (None when the service or date doesn't check out)."""
    timeline = next((t for t in data["timelines"] if t["id"] == service), None)
    if not timeline:
        return None
    try:
        applied_on = date.fromisoformat(applied) if applied else None
    except ValueError:
        applied_on = None
    if applied_on and not SAKALA_IN_FORCE <= applied_on <= clock_today():
        applied_on = None
    elapsed = working_days_since(applied_on, clock_today()) if applied_on else None
    status = wait_status(elapsed, timeline["days"])
    if timeline.get("excludes") and status != "within":
        status = "uncertain"  # the count includes a period (police verification) the promise leaves out
    return {"service": timeline["name"], "service_id": timeline["id"], "limit": timeline["limit"], "limit_days": timeline["days"],
            "condition": terms(timeline, data["profile"]), "excludes": timeline.get("excludes", ""), "allows": allows(data["profile"]),
            "applied": applied_on.isoformat() if applied_on else None, "elapsed": elapsed,
            "overdue": status == "past", "status": status}


def complaint(office_id: str, service: str = "", applied: str = "", number: str = "", today: date | None = None) -> dict[str, Any]:
    """A complaint letter about a late service, to the officer the Sakala compendium names. The citizen
    sends it themselves; nothing they type is stored."""
    data, o = find_office(office_id)
    profile, appeals = data["profile"], data["appeals"] or {}
    law = profile.get("promise", "the law") == "the law"
    act = profile.get("promise_name", "Karnataka Sakala Services Act, 2011")
    grievance = data.get("grievance") or {}
    out: dict[str, Any] = {
        "office": {"id": o["id"], "label": label(o), "email": o["email"], "address": o["address"]},
        "timelines": [{"id": t["id"], "name": t["name"], "limit": t["limit"]} for t in data["timelines"]],
        "officer": profile["officer"], "department": profile["department"], "helpline": data["helpline"],
        "first_appeal": appeals.get("first_appeal", ""), "draft": None, "problem": None,
        "promise_name": act, "grievance": grievance or None,
    }
    timeline = next((t for t in data["timelines"] if t["id"] == service), None)
    if not timeline:
        return out
    today, applied_on = today or clock_today(), None
    if applied:
        try:
            applied_on = date.fromisoformat(applied)
        except ValueError:
            out["problem"] = "That date wasn't understood, so the letter leaves it out."
    if applied_on and not SAKALA_IN_FORCE <= applied_on <= today:
        out["problem"], applied_on = "That date is in the future or too old to be covered, so the letter leaves it out.", None
    elapsed = working_days_since(applied_on, today) if applied_on else None
    overdue = elapsed is not None and elapsed > timeline["days"]
    uncertain = bool(overdue and timeline.get("excludes"))  # the count includes a period the promise leaves out
    overdue = overdue and not uncertain
    number = re.sub(r"[\r\n]+", " ", number).strip()[:40]
    name = f"{o['name']} ({o['code']})" if o["code"] else o["display_name"]
    page = f", page {timeline['page']}" if timeline.get("page") else ""
    to = next((x for x in data["offices"] if x["id"] == grievance.get("complaint_to")), o)  # passports: the RPO
    regarding = [f"Regarding my application at {name}", ""] if to is not o else []
    lines = [
        "To", f"The {profile['officer']}", to["name"] if to is not o else name, to["address"],
        grievance.get("complaint_email") or to["email"], "",
        f'Subject: {"Delay in" if overdue else "Status of my application for"} "{timeline["name"]}"'
        + (f" (application {number})" if number else "") + f", under the {act}", "",
        *regarding,
        "Sir/Madam,", "",
        f'I applied for the service "{timeline["name"]}"' + (f" on {applied_on.strftime('%d %B %Y')}" if applied_on else "")
        + (f" (application number {number})" if number else "") + (
            f". Under the {act}, this service is to be provided within {timeline['limit']} (Sakala Service Compendium, "
            f"05-05-2026{page})." if law else
            f". The {act} commits to providing this service within {timeline['limit']}"
            + (f", {timeline['condition']}" if timeline.get("condition") else ", from the receipt of complete documentation")
            + (f", excluding the {timeline['excludes']}" if timeline.get("excludes") else "") + "."), "",
    ]
    if overdue:
        lines += [f"About {elapsed} working days have passed since I applied, and my application has not been disposed of.", ""]
    elif uncertain:
        lines += [f"About {elapsed} working days have passed since I applied (including any {timeline['excludes']}), and my "
                  "application has not been disposed of.", ""]
    lines += ["I request you to dispose of my application without further delay, or to tell me in writing what is pending "
              "from my side.", ""]
    if not law and grievance:
        lines += [f"If this is not resolved, I will raise it through the Passport Seva grievance channels "
                  f"({', '.join(grievance.get('portals', []))}).", ""]
    if appeals.get("first_appeal"):
        lines += [f"The Sakala Service Compendium lists the {appeals['first_appeal']} as the authority for a first appeal "
                  "if a service is not provided in time.", ""]
    lines += ["Yours faithfully,", "[Your name]", "[Your phone number and address]", "[Date]"]
    out["office"]["email"] = grievance.get("complaint_email") or to["email"]
    out["draft"] = {"service": timeline["name"], "limit": timeline["limit"], "limit_days": timeline["days"], "uncertain": uncertain,
                    "excludes": timeline.get("excludes", ""),
                    "applied": applied_on.isoformat() if applied_on else None, "elapsed": elapsed, "overdue": overdue,
                    "subject": f"Delay in {timeline['name'].lower()}" if overdue else f"Status of {timeline['name'].lower()}",
                    "letter": "\n".join(lines)}
    return out


@lru_cache(maxsize=1)
def method() -> dict[str, Any]:
    """How well the review classifier works, computed now from the hand-labelled sets (as `kalaana evaluate`
    does), so the numbers the app shows can't drift from the code."""
    heldout = evaluate.load(evaluate.LABELS_DIR / "rto-reviews-heldout.jsonl")

    def score(predict: evaluate.Predictor) -> dict[str, Any]:
        results = evaluate.evaluate(heldout, predict)
        tp = sum(len(r.true_positives) for r in results.values())
        fp = sum(len(r.false_positives) for r in results.values())
        fn = sum(len(r.false_negatives) for r in results.values())
        return {"precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
                "flags_right": tp, "flags": tp + fp, "reports_found": tp, "reports": tp + fn,
                "categories": [{"category": r.category, "reviews": r.support, "precision": r.precision, "recall": r.recall}
                               for r in results.values()]}

    model = "gemma3:4b"
    return {"heldout_reviews": len(heldout), "office_type": "rto", "lexicon": score(evaluate.lexicon),
            "model_name": model, "model": score(refine.predictor(model)), "union": score(refine.predictor(model, combine=True))}
