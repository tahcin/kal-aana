"""Make review quotes safe to show: mask people's names and private phone numbers.

Reviews name officers and agents, sometimes to praise them and sometimes to accuse them. This
project reports what offices do, not what individuals do, so a quote never shows a name.
Masking is pattern-based: a name next to a title or role word ("Mr.", "officer", "madam",
"named"). Patterns can't catch a name with no cue at all ("approach Ishaan, who is helpful"),
so every quote is also read in full before it is published. Names found that way go in
data/private/names-to-mask.txt, one per line; that folder is never committed, because a list of
names is exactly what must not be published.
"""

from __future__ import annotations

import re
from functools import cache
from typing import Final

import phonenumbers

from . import phones
from .paths import DATA_DIR

MASK: Final = "[name]"

# A name: one to four words, each Capitalised or ALL CAPS, optionally after initials ("G. P.").
# Words may be joined by spaces, a slash or a hyphen ("Ujjwal/Siddhant").
_WORD: Final = r"(?:[A-Z][a-z]{2,}(?:[A-Z][a-z]+)*|[A-Z]{3,})"  # Jatin, ZubinKabir, TANVIR
_NAME: Final = rf"(?:(?:[A-Z]\.?\s?){{1,3}}\s*)?{_WORD}(?:(?:\s+|\s?[/-]\s?){_WORD}){{0,3}}"
_TITLES: Final = r"(?:Mr|Mrs|Ms|Dr|Sri|Shri|Shree|Sree|Smt|Kum|Sir|Madam|Mam|Ma'am)"
_ROLES: Final = (r"(?:officers?|officials?|inspectors?|clerks?|agents?|brokers?|RTO|ARTO|RO|ARO|AO|SR|staff|"
                 r"superintend[ae]nt|superident|suprident|supdt|advocates?|lawyers?|notary|doctor|"
                 r"person|lady|guy|named(?:\s+as)?|called|name\s+is|the\s+name|officers?\s+like|people\s+like)")
_HONORIFICS: Final = r"(?:sir|madam|mam|ma'am|garu|ji|anna|akka|saar)"

# Capitalised words that follow a role or title word but aren't names.
_NOT_NAMES: Final = frozenset({
    "Sir", "Madam", "Mam", "Office", "Officer", "Officers", "Official", "Officials", "Team", "Staff", "Room",
    "Counter", "Floor", "Bangalore", "Bengaluru", "Karnataka", "India", "Government", "Govt", "The", "This",
    "They", "Thank", "Thanks", "Please", "Very", "Good", "Worst", "Best", "Also", "Only", "Electronic", "City",
    "South", "North", "East", "West", "Central", "Online", "Parivahan", "Sarathi", "Vahan", "Google", "Bike",
    "Car", "Passport", "Anything", "Everything", "Nothing", "Inspector", "Agent", "Agents", "Broker", "FULL",
    "FRAUD", "RTO", "ARTO", "DL", "LL", "RC", "NOC", "KA", "OFFICE", "OFFICER", "AGENT", "SIR", "THE", "AND",
    "Regional", "Transport", "Assistant", "Senior", "Deputy", "Joint", "Commissioner",
    # Words that start a sentence before "agent" or follow "thanks to" without being a name.
    "One", "Every", "Each", "Any", "Another", "Some", "Same", "Other", "That", "These", "Those", "Which", "Our",
    "My", "His", "Her", "Their", "Your", "Local", "Private", "Driving", "School", "Real", "Fake", "Genuine",
    "Trusted", "First", "Second", "Last", "Next", "God", "All", "Everyone", "You", "Him", "Them",
    # Words shouted in quotes after "staff" ("staff 'SERVER DOWN'").
    "SERVER", "DOWN", "NOT", "WORKING", "CLOSED", "COME", "TOMORROW", "LUNCH", "WAIT", "BUSY", "NO",
    # Acronyms that follow "RTO" in reviews.
    "GPS", "PUC", "PUCC", "LLR", "DTO", "FIR", "OTP", "UPI", "PAN", "SMS", "MVI", "BBMP", "KSRTC", "ADTT", "LMV",
    "MCWG", "HSRP", "IDP", "CUG", "FC", "NOC", "SBI", "ATM", "PDF", "API", "URL", "QR",
})
# Lowercase words that can follow "Mr" without being a name ("Mr and Mrs", "Mr was").
_NOT_LOWER_NAMES: Final = (r"(?:and|or|the|was|is|who|has|had|have|from|did|does|will|can|could|would|should|very|also|sir|madam|"
                           r"for|are|were|not|came|went|said|told|asked|gave|took|helped|got|says|at|in|on|to|of|with)\b")

# Role and title words match in any case; a name must start with a capital letter.
_PATTERNS: Final = (
    re.compile(rf"\b(?i:{_TITLES})\.?\s*({_NAME})"),  # Mr. Bhavesh, Mrs  Yamini, Mr.EHSAN
    re.compile(rf"\b(?i:{_ROLES})[ \t]+[\"'“]?[ \t]*({_NAME})"),  # officer Ketaki, named "TANVIR", RO Siddhant
    re.compile(rf"\b({_NAME})\s+(?i:{_HONORIFICS})\b"),  # Ketaki madam, Ishaan sir
    re.compile(rf"\b(?:to|with|by|from|contact|approach|met|meet|via)\s+({_NAME})\s+(?i:agent|broker|middle\s?man)\b"),  # to Rehaan agent
    re.compile(rf"\b(?i:kudos|thanks|thank\s+you|grateful|thankful|shout\s?out)\s+(?i:to\s+)?({_NAME})"),  # Kudos to Jatin
    re.compile(rf"@\s?({_NAME})"),  # @Aarav
    re.compile(rf"\b(?:Mr|Mrs|Ms|Dr|Shri|Sri|Smt)\.?[ \t]+(?!{_NOT_LOWER_NAMES})([a-z]{{3,}})\b"),  # Mr tanvir
    re.compile(rf"\b(?i:regards|rgds|thanks|thank\s+you|cheers)\s*,\s*({_NAME})\s*$"),  # a sign-off
    re.compile(rf"\b(?i:named(?:\s+as)?|called)\s+{_NAME}\s+(?:and|&)\s+({_NAME})"),  # the second of two names
)
_TOKEN: Final = re.compile(r"[A-Za-z][A-Za-z.]*")
_TRAILING_INITIAL: Final = re.compile(r"\s[B-HJ-Z]\b\.?")  # "Rehaan K." (not "I" or "A", which are words)
LOCAL_NAMES: Final = DATA_DIR / "private" / "names-to-mask.txt"


@cache
def local_names() -> frozenset[str]:
    """Names a person found while reading the quotes, kept out of the repository."""
    try:
        lines = LOCAL_NAMES.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return frozenset()
    return frozenset(name for line in lines if (name := line.strip()) and not name.startswith("#"))


def _name_span(text: str, start: int, end: int, keep: frozenset[str]) -> tuple[int, int] | None:
    """The part of a candidate that is a name: up to the first word that isn't one
    ("Bhavesh Regional Transport" -> "Bhavesh"). None if it holds no name at all."""
    last = None
    for token in _TOKEN.finditer(text, start, end):
        word = token.group(0).rstrip(".")
        if len(word) > 1 and (word in _NOT_NAMES or word in keep):
            break
        if len(word) > 1:
            last = token.end()
    return (start, last) if last else None


def mask_listed(text: str, names: frozenset[str]) -> str:
    """Mask only the listed names, wherever they appear. For text that isn't a review (Google's AI answers), where
    the cue patterns ("Official ...", "RTO ...") would mask ordinary words like "Website" or "Code"."""
    for name in sorted(names, key=len, reverse=True):
        text = re.sub(rf"(?<![\w]){re.escape(name)}(?![\w])", "[name]", text, flags=re.I)
    return text


def mask_names(text: str, keep: frozenset[str] = frozenset(), names: frozenset[str] = frozenset()) -> str:
    """Replace names of people with [name]. `keep` lists words that aren't names here, e.g. place names;
    `names` lists names to mask wherever they appear, cue or not."""
    spans: list[tuple[int, int]] = []
    for pattern in _PATTERNS:
        for m in pattern.finditer(text):
            span = _name_span(text, *m.span(1), keep)
            if span:
                initial = _TRAILING_INITIAL.match(text, span[1])
                spans.append((span[0], initial.end() if initial else span[1]))
    for name in names:
        spans += [m.span() for m in re.finditer(rf"(?<![\w]){re.escape(name)}(?![\w])", text, re.I)]
    merged: list[list[int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    for start, end in reversed(merged):
        text = text[:start] + MASK + text[end:]
    return text


# A vehicle registration ("KA 99 ZZ 1234") identifies its owner; an agent's shop or stall number
# ("shop no 45") points at one person as surely as a name does.
_VEHICLE: Final = re.compile(r"\b[A-Z]{2}[ -]?\d{1,2}[ -]?[A-Za-z]{1,3}[ -]?\d{4}\b"  # KA 99 ZZ 1234
                             r"|\b\d{2}[ -]?BH[ -]?\d{4}[ -]?[A-Z]{1,2}\b")  # Bharat series: 22 BH 1234 AB
_SHOP: Final = re.compile(r"(?i)\b((?:shop|stall)\s*(?:no\.?|number|num|#)\s*)\d+\b")
VEHICLE_MASK: Final = "[vehicle number]"


def mask_identifiers(text: str) -> str:
    """Hide vehicle registration numbers and agents' shop or stall numbers."""
    return _SHOP.sub(r"\1[number]", _VEHICLE.sub(VEHICLE_MASK, text))


def mask_phones(text: str, official: frozenset[str] = frozenset()) -> str:
    """Hide the middle digits of every mobile number in the text, however it's written, except
    `official` ones (phone keys from the directory). Landlines and toll-free numbers stay visible:
    they belong to offices, not people."""
    spans: list[tuple[int, int, str]] = []
    for match in phonenumbers.PhoneNumberMatcher(text, "IN", leniency=phonenumbers.Leniency.VALID):
        phone = phones.parse(match.raw_string)
        if phone and phone.masked != phone.display and phone.key not in official:
            spans.append((match.start, match.end, phone.masked))
    for start, end, masked in sorted(spans, reverse=True):
        text = text[:start] + masked + text[end:]
    return text


_EMAIL: Final = re.compile(r"\b[\w.+-]+@([\w-]+(?:\.[\w-]+)+)\b")
_GOV_DOMAIN: Final = re.compile(r"(?:^|\.)(?:gov\.in|nic\.in)$", re.I)
EMAIL_MASK: Final = "[email]"


def mask_emails(text: str, official: frozenset[str] = frozenset()) -> str:
    """Hide email addresses that aren't on a government domain or in the directory (`official`, lower case).
    An address Google attributes to an office isn't checked, and may be someone's own."""
    return _EMAIL.sub(lambda m: m.group(0) if _GOV_DOMAIN.search(m.group(1)) or m.group(0).lower() in official
                      else EMAIL_MASK, text)


_SOCIAL_TITLE: Final = re.compile(r"\(@[\w.]+\)|^(?:Reel|Post|Video|Photo)s? by\b", re.I)


def source_title(title: str, link: str) -> str:
    """A cited page's title, unless it names a social media account: then only the site."""
    if not _SOCIAL_TITLE.search(title):
        return title
    site = re.sub(r"^https?://(?:www\.)?([^/]+).*$", r"\1", link or "") or "social media"
    return f"A post on {site}"


def safe_quote(text: str, keep: frozenset[str] = frozenset()) -> str:
    return mask_phones(mask_identifiers(mask_names(text, keep, local_names())))
