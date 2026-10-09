"""Which office a person means: by RTO code ("KA-05", "ka 5") or by whole words of its name or address.

Shared by the MCP server (an assistant names an office) and the ask box on the web app (a citizen
describes their problem). A neighbourhood alone is not an office: when two offices fit equally
well, the caller is told which, and asks.
"""

from __future__ import annotations

import re
from typing import Any, Final

# Words that say which kind of office is meant. "registration" is left out: RTOs register vehicles.
TYPE_WORDS: Final = {
    "rto": frozenset({"rto", "rtos", "arto", "transport", "driving", "licence", "license", "ll", "dl", "vehicle", "rc"}),
    "subregistrar": frozenset({"sub", "registrar", "subregistrar", "sro", "property", "marriage", "encumbrance", "ec",
                               "sale", "deed"}),
    "passport": frozenset({"passport", "psk", "popsk", "rpo", "tatkal", "tatkaal", "pcc"}),
}
# Words that name every office (or none) and so can't tell offices apart.
_STOPWORDS: Final = frozenset({
    "regional", "office", "offices", "bengaluru", "bangalore", "blr", "nagar", "layout",
    "road", "rd", "main", "assistant", "stage", "phase", "near", "the", "of", "and", "no", "survey", "hobli",
    "village", "karnataka", "sector", "block", "cross", "number", "phone", "contact", "in", "at", "for", "me",
    "s", "registrars", "registration", "registry", "floor", "building", "complex", "opp", "bangalore",
}).union(*TYPE_WORDS.values())


class NoSuchOffice(LookupError):
    """Nothing matches, or several offices match equally well (`candidates`)."""

    def __init__(self, message: str, candidates: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.candidates = candidates or []


def label(office: dict[str, Any]) -> str:
    return f"{office['code']} {office['name']}" if office["code"] else office["display_name"]


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS]


def joined(words: list[str]) -> set[str]:
    """Runs of adjacent words written together: "k r puram" -> "kr", "krpuram", "rpuram"."""
    return {"".join(words[i:j]) for i in range(len(words)) for j in range(i + 2, len(words) + 1)}


def vocabulary(office: dict[str, Any]) -> set[str]:
    """Words that identify an office: its address and PIN (3+ characters, so a door number such as "3"
    doesn't count), and its name and aliases (2+ letters, so "JP" does), plus their joined forms."""
    address = {w for w in tokens(office["address"]) if len(w) > 2}
    names = [tokens(n) for n in (office["name"], *office.get("aliases", []))]
    return address | {w for n in names for w in n if len(w) > 1} | {w for n in names for w in joined(n)}


# Name words that also mean something else in a sentence ("I live in the east", "the city RTO"): they pick an
# office only when the message also says which kind of office.
_WEAK_NAME_WORDS: Final = frozenset({"north", "south", "east", "west", "central", "electronic"})
# Too common in a sentence to name an office at all ("Sri Lakshmi", "the city office").
_NEVER_ALONE: Final = frozenset({"city", "town", "new", "old", "sri", "shri"})


def name_vocabulary(office: dict[str, Any]) -> set[str]:
    """Words of an office's name and aliases (and their joined forms), plus its PIN: what a person would say."""
    names = [tokens(n) for n in (office["name"], *office.get("aliases", []))]
    return {w for n in names for w in n if len(w) > 1} | {w for n in names for w in joined(n)} | {office.get("pincode", "")} - {""}


def names_in(query: str, office: dict[str, Any]) -> bool:
    """Does the query contain the office's whole name (every distinctive word of it, or of an alias)?"""
    words = set(tokens(query)) | joined(tokens(query))
    return any(n and set(n) <= words for n in (tokens(office["name"]), *(tokens(a) for a in office.get("aliases", []))))


# "I live in Whitefield", "we stay near Jalahalli": where someone lives is not the office they mean.
_HOME: Final = re.compile(r"\b(?:i|we)(?:\s+am|'m)?\s+(?:live|living|stay|staying|reside|residing|from)\s+(?:in|at|near|around)?\s*"
                          r"([a-z0-9 ]+?)(?=\s*(?:[,.;!?]|\b(?:and|but|so|my|i|we|since|for|applied)\b|$))", re.I)


def without_home(text: str) -> str:
    return _HOME.sub(" ", text)


def _known(offices: list[dict[str, Any]]) -> str:
    return "; ".join(label(o) for o in offices)


def find_office(query: str, snapshots: dict[str, dict[str, Any]], office_type: str | None = None,
                free_text: bool = False) -> dict[str, Any]:
    """The office a query names, from `snapshots` (office type -> snapshot), narrowed by words naming its
    type ("RTO", "sub-registrar"). Raises NoSuchOffice when nothing matches or two offices tie.

    `free_text` is for a citizen's whole sentence rather than an office name: only words of an office's name
    (or its PIN) count, not words of its address, and direction-like name words ("south") count only when the
    sentence also says which kind of office."""
    words = set(re.findall(r"[a-z0-9]+", query.lower()))
    named_types = [t for t, w in TYPE_WORDS.items() if words & w]
    types = [office_type] if office_type else named_types or list(snapshots)
    offices = [o for t in types if t in snapshots for o in snapshots[t]["offices"]]
    code = re.search(r"\bka\s*-?\s*0?(\d{1,2})\b", query, re.I)
    if code and "rto" in snapshots:
        wanted = f"KA-{int(code.group(1)):02d}"
        match = next((o for o in snapshots["rto"]["offices"] if o["code"] == wanted), None)
        if match:
            return match
        raise NoSuchOffice(f"There is no Bengaluru RTO with code {wanted}. Known RTOs: {_known(snapshots['rto']['offices'])}")
    words_in_query = tokens(without_home(query) if free_text else query)
    found = set(words_in_query) | joined(words_in_query)  # "J P Nagar" also reads as "jp"
    if "regional" in words and "passport" in words:
        words = words | {"rpo"}
    # A kind only one office has ("RPO", "POPSK") names that office, though the word is also a type word.
    kinds = [o.get("kind", "").lower() for o in offices]
    unique_kind = {k for k in kinds if k and kinds.count(k) == 1 and k in words}
    if free_text:
        found -= _NEVER_ALONE
        if not (named_types or office_type):
            found -= _WEAK_NAME_WORDS
    typed = bool(named_types or office_type)

    def score(o: dict[str, Any]) -> int:
        named = len(found & name_vocabulary(o))  # words of its name count double: "BDA" names one office, and is
        hits = named if free_text else named + len(found & vocabulary(o))  # only in the address of two others
        hits += 2 if o.get("kind", "").lower() in unique_kind else 0
        return hits + (10 if typed and hits and names_in(query, o) else 0)  # "Jala sub-registrar" outright wins a tie

    scored = sorted(((score(o), o) for o in offices), key=lambda s: s[0], reverse=True)
    if not (found or unique_kind) or not scored or scored[0][0] == 0:
        raise NoSuchOffice(f"No Bengaluru office matches {query!r} by code or name. A neighbourhood is not an office; "
                           f"ask the user which office, from: {_known(offices)}")
    if len(scored) > 1 and scored[1][0] == scored[0][0]:
        tied = [o for n, o in scored if n == scored[0][0]]
        hint = " Say 'RTO' or 'sub-registrar' to choose." if len({o["office_type"] for o in tied}) > 1 else ""
        raise NoSuchOffice(f"{query!r} could be any of: {_known(tied)}. Ask which one.{hint}", tied)
    return scored[0][1]
