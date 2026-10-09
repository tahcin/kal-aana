"""The ask box: a citizen describes their problem in their own words, and Kal Aana works out the office,
the service, when they applied and what they need, then answers from the snapshot.

The reading is done by rules (tested, offline, free). Every field it fills is checked against the data:
an office must exist, a service must be one with a Sakala timeline, a date can't be in the future.
Kal Aana stores and logs nothing the person types (a configured model reader receives it to read it).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Final, Literal

from . import lookup, reader, views

Intent = Literal["late", "reach", "report", "overview"]
MAX_CHARS: Final = 400

# Service ids (from the official timelines) and the ways people write them, most specific first.
SERVICES: Final[list[tuple[str, re.Pattern[str]]]] = [(sid, re.compile(p, re.I)) for sid, p in [
    ("passport-tatkaal", r"tatk(?:aa?)?l"),
    ("police-clearance-certificate", r"police clearance|\bpcc\b"),
    ("passport-reissue", r"passport\b.*\b(re-?issue|renew)|(re-?issue|renew)\w*\b.*\bpassport"),
    ("passport-fresh", r"(new|fresh|first)\b.*\bpassport|passport\b.*\b(application|applied)"),
    ("duplicate-learners-licence", r"duplicate\b.*\b(learner|(?<!['’])ll\b)|\b(learner|(?<!['’])ll)\b.*\bduplicate"),
    ("learners-licence", r"learn[ae]r|lerner|(?<!['’])\bll\b|learning licen[cs]e"),
    ("duplicate-licence", r"duplicate\b.*\b(driving licen[cs]e|dl\b|licen[cs]e)|lost (my )?(dl|driving licen[cs]e|licen[cs]e)"),
    ("licence-renewal", r"renew\w*\b.*\b(dl|licen[cs]e)|(dl|licen[cs]e)\b.*\brenew"),
    ("add-vehicle-class", r"add\w*\b.*\bclass|class of vehicle"),
    ("international-driving-permit", r"international (driving )?(permit|licen[cs]e)|\bidp\b"),
    ("driving-licence", r"driving licen[cs]e|\bdl\b|permanent licen[cs]e|driving test"),
    ("duplicate-rc", r"duplicate\b.*\b(rc|registration certificate)|lost (my )?rc\b"),
    ("rc-renewal", r"renew\w*\b.*\b(rc|registration certificate)|(rc|registration certificate)\b.*\brenew"),
    ("temporary-registration", r"temporary registration|\btr\b"),
    ("transfer-of-ownership", r"transfer|ownership|second[- ]hand"),
    ("hypothecation", r"hypothecation|\bloan\b|\bhp\b"),
    ("clearance-certificate", r"\bnoc\b|clearance certificate"),
    ("vehicle-registration", r"vehicle registration|register\w*\b.*\b(car|bike|scooter|vehicle)|new (car|bike|scooter|vehicle)|number plate"),
    ("encumbrance-certificate-pre-2004", r"(encumbrance|\bec\b).*(before|pre)[- ]?2004|old (encumbrance|ec)\b"),
    ("encumbrance-certificate", r"encumbrance|\bec\b"),
    ("certified-copy", r"certified cop"),
    ("marriage-registration-special", r"special marriage"),
    ("marriage-registration-hindu", r"marriage|marrige|marraige|shaadi"),
    ("property-registration", r"sale deed|gift deed|property|regist\w*\b.*\b(flat|site|plot|land|house)\b|\b(flat|site|plot|land|house)\b.*\bregist|"
                              r"registration of (a |my )?document"),
]]
INTENTS: Final[list[tuple[Intent, re.Pattern[str]]]] = [
    ("report", re.compile(r"bribe|\bagent|broker|middle ?man|extra money|asked (for )?money|lanch", re.I)),
    ("late", re.compile(r"\blate\b|delay|pending|waiting|\bstuck\b|not (yet )?(received|approved|come|got|issued|done)|"
                        r"still (not|no|nothing|waiting)|no approval|\batk[ae]\b|nahi (aaya|aayi|mila|mili)|haven'?t (got|received)|no (update|response)|complain|overdue", re.I)),
    ("reach", re.compile(r"number|phone|call|contact|reach|email|helpline|address|where is|timing|open", re.I)),
]
_MONTHS: Final = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
# A month as people write it: "Sep", "Sept", "September", never the start of another word ("10 marriages").
_MONTH: Final = (r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
                 r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b\.?")
_WORD_NUMBERS: Final = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "ten": 10, "ek": 1, "do": 2, "teen": 3}
# Units as people write them, in English and Hinglish ("2 mahine se", "10 din").
_UNITS: Final = {"day": 1, "days": 1, "din": 1, "week": 7, "weeks": 7, "hafta": 7, "hafte": 7, "month": 30, "months": 30,
                 "mahina": 30, "mahine": 30}
_UNIT: Final = r"(days?|weeks?|months?|din|hafta|hafte|mahina|mahine)"
_NUMBER: Final = r"(\d{1,3}|a|an|one|two|three|four|five|six|ten|ek|do|teen)"


# Hindi (Devanagari) and Kannada words the rules need, in English, so a question in either script can be read
# without a model. Only words that name a service, an office, a time span or a wait; anything else is left as is.
_SCRIPT_WORDS: Final = [(re.compile(p), en) for p, en in [
    (r"लर्नर|लर्निंग|ಕಲಿಕಾ|ಲರ್ನರ್|ಎಲ್‌?ಎಲ್", "learner"), (r"ड्राइविंग|ಡ್ರೈವಿಂಗ್", "driving"),
    (r"लाइसेंस|लायसेंस|ಲೈಸೆನ್ಸ್|ಪರವಾನಗಿ", "licence"), (r"पासपोर्ट|ಪಾಸ್‌?ಪೋರ್ಟ್", "passport"),
    (r"तत्काल|ತತ್ಕಾಲ್", "tatkaal"), (r"नवीनीकरण|रिन्यू|ನವೀಕರಣ|ರಿನ್ಯೂ", "renewal"),
    (r"आरटीओ|आर\s?टी\s?ओ|ಆರ್‌?ಟಿಒ", "RTO"), (r"सब[- ]?रजिस्ट्रार|ಉಪ\s?ನೋಂದಣಿ|ಸಬ್\s?ರಿಜಿಸ್ಟ್ರಾರ್", "sub-registrar"),
    (r"संपत्ति|प्रॉपर्टी|ಆಸ್ತಿ", "property"), (r"रजिस्ट्री|पंजीकरण|ನೋಂದಣಿ", "registration"),
    (r"विवाह|शादी|ಮದುವೆ|ವಿವಾಹ", "marriage"), (r"ऋणभार|ಋಣಭಾರ", "encumbrance"),
    (r"साउथ|दक्षिण|ಸೌತ್|ದಕ್ಷಿಣ", "south"), (r"नॉर्थ|उत्तर|ನಾರ್ತ್|ಉತ್ತರ", "north"), (r"ईस्ट|पूर्व|ಈಸ್ಟ್|ಪೂರ್ವ", "east"),
    (r"वेस्ट|पश्चिम|ವೆಸ್ಟ್|ಪಶ್ಚಿಮ", "west"), (r"सेंट्रल|ಸೆಂಟ್ರಲ್", "central"),
    (r"ಯಲಹಂಕ|येलहंका", "Yelahanka"), (r"ಜಯನಗರ|जयनगर", "Jayanagar"), (r"ಕೋರಮಂಗಲ|कोरमंगला", "Koramangala"),
    (r"ಲಾಲ್‌?ಬಾಗ್|लालबाग", "Lalbagh"), (r"ವೈಟ್‌?ಫೀಲ್ಡ್|व्हाइटफील्ड", "Whitefield"), (r"ಜಾಲಹಳ್ಳಿ|जालाहल्ली", "Jalahalli"),
    (r"ರಾಜಾಜಿನಗರ|राजाजीनगर", "Rajajinagar"), (r"ಇಂದಿರಾನಗರ|इंदिरानगर", "Indiranagar"), (r"ಬಸವನಗುಡಿ|बसवनगुडी", "Basavanagudi"),
    (r"हफ्ते|हफ़्ते|सप्ताह|ವಾರ", "weeks"), (r"महीने|महीना|ತಿಂಗಳ\w*", "months"), (r"दिन|ದಿನ\w*", "days"),
    (r"पहले|ಹಿಂದೆ|ಇಂದ\b", "ago"), (r"अटका|अटकी|रुका|ಬಾಕಿ|ಸ್ಥಗಿತ", "pending, still waiting"),
    (r"नहीं आया|नहीं मिला|ಬಂದಿಲ್ಲ|ಸಿಕ್ಕಿಲ್ಲ", "not received"), (r"नंबर|फोन|ಸಂಖ್ಯೆ|ಫೋನ್", "phone number"),
    (r"रिश्वत|ಲಂಚ", "bribe"), (r"दलाल|एजेंट|ಏಜೆಂಟ್|ದಲ್ಲಾಳಿ", "agent"),
    (r"\bएक\b|ಒಂದು", "one"), (r"\bदो\b|ಎರಡು", "two"), (r"\bतीन\b|ಮೂರು", "three"), (r"\bचार\b|ನಾಲ್ಕು", "four"),
]]
_DIGITS: Final = str.maketrans("०१२३४५६७८९೦೧೨೩೪೫೬೭೮೯", "01234567890123456789")


def in_latin(text: str) -> str:
    """The text with Hindi and Kannada digits and key words also given in English, for the rules to read. A message
    already in Latin script comes back unchanged."""
    if not re.search(r"[\u0900-\u097F\u0C80-\u0CFF]", text):
        return text
    out = text.translate(_DIGITS)
    for pattern, english in _SCRIPT_WORDS:
        out = pattern.sub(f" {english} ", out)
    # "<n> months ago": a span written as "since n months" in either language, once the words are in English
    out = re.sub(r"(\d+|one|two|three|four)\s+(weeks|months|days)\s+(?!ago)", r"\1 \2 ago ", out)
    return re.sub(r"\s+", " ", out).strip()


def find_service(text: str) -> str | None:
    return next((sid for sid, pattern in SERVICES if pattern.search(text)), None)


def find_intent(text: str) -> Intent:
    return next((intent for intent, pattern in INTENTS if pattern.search(text)), "overview")


def find_date(text: str, today: date) -> tuple[date | None, str]:
    """When they applied: an explicit date, or "3 weeks ago"-style (approximate). Never in the future."""
    found: date | None = None
    how = ""
    if m := re.search(r"\b(20\d\d)-(\d\d)-(\d\d)\b", text):
        found, how = _safe(int(m[1]), int(m[2]), int(m[3])), "the date you gave"
    elif m := re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](20\d\d)\b", text):  # Indian order: day first
        found, how = _safe(int(m[3]), int(m[2]), int(m[1])), "the date you gave"
    elif m := re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?" + _MONTH + r"(?:,?\s+(20\d\d))?", text, re.I):
        found, how = _safe(int(m[3] or today.year), _MONTHS[m[2][:3].lower()], int(m[1])), "the date you gave"
    elif m := re.search(r"\b" + _MONTH + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s+(20\d\d))?", text, re.I):
        found, how = _safe(int(m[3] or today.year), _MONTHS[m[1][:3].lower()], int(m[2])), "the date you gave"
    # "3 weeks ago", "applied 20 days back", "it's been a month": time since applying. "3 weeks late" or "a 30 day
    # limit" is not a date, so a bare duration counts only before "ago/back" or after "applied/been/waiting".
    elif m := (re.search(rf"\b{_NUMBER}\s+{_UNIT}\s+(?:ago|back|before|se|from|pehle)\b", text, re.I)
               or re.search(rf"\b(?:applied|submitted|been|waiting|pending|for the (?:last|past)|since)\s+(?:for\s+)?"
                            rf"(?:about\s+|over\s+|almost\s+|more than\s+)?{_NUMBER}\s+{_UNIT}\b", text, re.I)
               or _bare_wait(text)):
        n = int(m[1]) if m[1].isdigit() else _WORD_NUMBERS[m[1].lower()]
        unit = {1: "day", 7: "week", 30: "month"}[_UNITS[m[2].lower()]]
        found, how = today - timedelta(days=_UNITS[m[2].lower()] * n), f"about {n} {unit}{'s' if n != 1 else ''} ago, from what you wrote"
    if found and found > today and how == "the date you gave" and not re.search(r"20\d\d", text):
        found = _safe(found.year - 1, found.month, found.day)  # "12 Dec" said in October means last December
    if found is None or found > today or found < views.SAKALA_IN_FORCE:
        return None, ""
    return found, how


def _bare_wait(text: str) -> re.Match[str] | None:
    """A bare duration in a message about waiting ("not received 40 days"), but not a promise or a limit
    ("they said 7 days", "a 30 day limit", "3 weeks late")."""
    if find_intent(text) != "late":
        return None
    for m in re.finditer(rf"\b{_NUMBER}[\s-]+{_UNIT}\b", text, re.I):
        before, after = text[max(0, m.start() - 25):m.start()].lower(), text[m.end():m.end() + 12].lower()
        if not re.search(r"said|promis|within|takes?|should|limit|deadline|only|in$|of$", before) and \
                not re.search(r"^\W*(late|limit|deadline|delay|overdue|time ?limit|max)", after):
            return m
    return None


def _safe(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _summary(o: dict[str, Any]) -> dict[str, str]:
    return {"id": o["id"], "label": lookup.label(o), "type": o["office_type"]}


def understand(text: str, today: date | None = None, use_model: bool = True) -> dict[str, Any]:
    """Read a citizen's free text into an office, a service, a date and an intent. A configured model
    (reader.py) proposes the fields first; each is kept only if it checks out, else the rules decide."""
    text = in_latin(text[:MAX_CHARS])
    today = today or views.clock_today()
    snapshots = {t: views.load(views.CITY, t) for t in views.office_types()}
    service_ids = [x["id"] for data in snapshots.values() for x in data["timelines"]]
    by, note = "rules", ""
    try:
        model = reader.read(text, service_ids, today.isoformat()) if use_model else None
    except Exception:  # ReaderError, or anything unexpected from a model's SDK: the rules always answer
        model, note = None, "The model reader wasn't available, so the rules read it instead."
    service = model.service if model and model.service in service_ids else find_service(text)
    service_type = next((t for t, data in snapshots.items() if any(x["id"] == service for x in data["timelines"])), None)
    office, candidates = None, []
    for attempt in ([model.office] if model and model.office else []) + [text]:
        try:
            narrow = service_type if service_type and not re.search(r"\bka\s*-?\s*\d", attempt, re.I) else None
            office, candidates = lookup.find_office(attempt, snapshots, narrow, free_text=attempt is text), []
            break
        except lookup.NoSuchOffice as e:
            candidates = candidates or [_summary(o) for o in e.candidates][:6]
    if office and service_type and office["office_type"] != service_type:
        service = None  # a property service at an RTO: keep the office, drop the service
    applied, applied_how = None, ""
    if model and model.applied:
        try:
            given = date.fromisoformat(model.applied)
            if views.SAKALA_IN_FORCE <= given <= today:
                rules_date, rules_how = find_date(text, today)
                # A date the model worked out from "3 weeks ago" is still approximate; say so.
                applied, applied_how = given, (rules_how if rules_date == given and rules_how.startswith("about")
                                               else "the date read from your message")
        except ValueError:
            pass
    if applied is None:
        applied, applied_how = find_date(text, today)
    intent = model.intent if model and model.intent in ("late", "reach", "report", "overview") else find_intent(text)
    if model:
        by = model.by
    return {"office": _summary(office) if office else None, "candidates": candidates, "service": service,
            "applied": applied.isoformat() if applied else None, "applied_how": applied_how, "intent": intent,
            "by": by, "note": note}


def answer(text: str, today: date | None = None, use_model: bool = True, got: dict[str, Any] | None = None) -> dict[str, Any]:
    """The understanding (`got`, if already read) plus an answer built only from the snapshot."""
    got = got or understand(text, today, use_model)
    out: dict[str, Any] = {"understood": got, "by": got["by"], "answer": None}
    if not got["office"]:
        if got["service"] and not got["candidates"] and not got["note"]:
            got["note"] = "We understood the service but not which office. Name it, for example \"Jayanagar sub-registrar\" or \"RTO Yelahanka\"."
        return out
    data, o = views.find_office(got["office"]["id"])
    card = views.story_card(o, data)
    timeline = next((t for t in data["timelines"] if t["id"] == got["service"]), None)
    lines: list[str] = []
    headline = ""
    if timeline and got["applied"]:
        letter = views.complaint(o["id"], service=timeline["id"], applied=got["applied"], today=today)["draft"] or {}
        elapsed = letter.get("elapsed")
        if elapsed is not None:
            headline = views.wait_sentence(elapsed, timeline["limit"], timeline["days"], views.terms(timeline, data["profile"]),
                                           views.allows(data["profile"]))
    elif timeline:
        headline = (f"{timeline['name']}: {views.allows(data['profile'])} {timeline['limit']}"
                    + (f", {views.terms(timeline, data['profile'])}" if views.terms(timeline, data["profile"]) else "")
                    + f", at {lookup.label(o)}.")
    if timeline and timeline["id"] == "passport-reissue" and not re.search(r"police|verification", text, re.I):
        pv = next((t for t in data["timelines"] if t["id"] == "passport-reissue-pv"), None)
        if pv:
            if headline:
                headline += " That assumes no police verification is needed."
            lines.append(f"If police verification is needed, the charter promises {pv['limit']}, excluding the verification period."
                         if headline else f"This assumes no police verification is needed; if it is, the charter promises "
                         f"{pv['limit']}, excluding the verification period.")
    if timeline and timeline["id"] == "marriage-registration-hindu" and not re.search(r"hindu", text, re.I):
        special = next((t for t in data["timelines"] if t["id"] == "marriage-registration-special"), None)
        if special:
            lines.append(f"This assumes the Hindu Marriage Act; under the Special Marriage Act the limit is {special['limit']}, on the same condition.")
    if card["official"]:
        first = card["official"][0]
        lines.append(f"The office's own number: {first['display']} ({first['label']}, from the {views.possessive(card['department'])} directory).")
    lines.extend(card["verdict"][:2])
    if not headline:
        headline = lines.pop(0) if lines else lookup.label(o)
    query = "&".join(f"{k}={v}" for k, v in (("service", timeline and timeline["id"]), ("applied", timeline and got["applied"])) if v)
    actions = [{"label": "Replay what Google shows for this office", "href": f"/?office={o['id']}" + (f"&{query}" if query else "") + "#replay"},
               {"label": "See all the evidence", "href": f"/office/{o['id']}"}]
    if got["intent"] == "report":  # what reviewers say about agents and bribes here, with the quotes
        actions.insert(0, {"label": "What reviewers report here", "href": f"/office/{o['id']}"})
        lines.append("Kal Aana doesn't take reports. Reviews of this office that mention agents or bribes are on its evidence page.")
    elif got["intent"] == "late" or (timeline and got["applied"]):
        actions.insert(0, {"label": "Draft a complaint letter", "href": f"/office/{o['id']}/complaint" + (f"?{query}" if query else "")})
    out["answer"] = {"headline": headline, "lines": lines, "official": card["official"],
                     "service": {"id": timeline["id"], "name": timeline["name"], "limit": timeline["limit"]} if timeline else None,
                     "actions": actions}
    return out
