"""Find and normalise Indian phone numbers in search-result text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property

import phonenumbers
from phonenumbers import PhoneNumberFormat, PhoneNumberType, geocoder

KIND_BY_TYPE = {
    PhoneNumberType.MOBILE: "mobile",
    PhoneNumberType.FIXED_LINE: "landline",
    # India's numbering plan overlaps here (the same ten-digit shape can be a district landline or a mobile),
    # so don't guess: callers that know the context can resolve it.
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
    PhoneNumberType.TOLL_FREE: "toll_free",
    PhoneNumberType.SHARED_COST: "shared_cost",
}

# TRAI's 1600-series for banks and financial institutions is not in libphonenumber yet.
_BFSI_1600 = re.compile(r"(?<!\d)1600[\s-]?\d{2,3}[\s-]?\d{3,4}(?!\d)")


@dataclass(frozen=True)
class Phone:
    key: str  # canonical id, e.g. +918068727374 or +9118002585603
    kind: str  # mobile | landline | fixed_or_mobile | toll_free | shared_cost | bfsi_1600
    raw: str = ""

    @cached_property
    def _number(self) -> phonenumbers.PhoneNumber:
        return phonenumbers.parse(self.key)

    @property
    def display(self) -> str:
        """Human format: 080 2663 0989, 94498 63448, 1800 258 1800."""
        if self.kind == "bfsi_1600":
            return self.key[3:]
        if self.kind == "mobile":
            return f"{self.key[-10:-5]} {self.key[-5:]}"
        return phonenumbers.format_number(self._number, PhoneNumberFormat.NATIONAL)

    @property
    def area_code(self) -> str:
        """STD code without the trunk 0 for landlines ("80" for Bengaluru), else "".

        Numbers that could be a mobile or a landline get no area code: reading 72045 as an STD
        code in a Jio mobile would be wrong, and claiming either would be a guess.
        """
        if self.kind != "landline":
            return ""
        length = phonenumbers.length_of_geographical_area_code(self._number)
        return phonenumbers.national_significant_number(self._number)[:length] if length else ""

    @property
    def region(self) -> str:
        """Where the STD code belongs, e.g. "Bangalore, Karnataka". Empty for non-geographic numbers."""
        if not self.area_code:
            return ""
        place = geocoder.description_for_number(self._number, "en")
        return "" if place == "India" else place

    @property
    def masked(self) -> str:
        """Hide the middle digits of numbers that may be private mobiles in public output."""
        if self.kind not in ("mobile", "fixed_or_mobile"):
            return self.display
        digits = self.key[-10:]
        return f"{digits[:2]}••• •••{digits[-2:]}"  # 4 of 10 digits: enough to tell numbers apart on screen


def _from_parsed(num: phonenumbers.PhoneNumber, raw: str) -> Phone | None:
    if num.country_code != 91 or not phonenumbers.is_valid_number(num):
        return None
    kind = KIND_BY_TYPE.get(phonenumbers.number_type(num))
    if not kind:
        return None
    return Phone(key=phonenumbers.format_number(num, PhoneNumberFormat.E164), kind=kind, raw=raw)


def parse(text: str) -> Phone | None:
    """Parse a single number such as a Maps `phone` field."""
    if not text:
        return None
    text = text.strip()
    m = _BFSI_1600.fullmatch(text)
    if m:
        digits = re.sub(r"\D", "", text)
        return Phone(key=f"+91{digits}", kind="bfsi_1600", raw=text)
    try:
        return _from_parsed(phonenumbers.parse(text, "IN"), text)
    except phonenumbers.NumberParseException:
        return None


def find_all(text: str) -> list[Phone]:
    """Find every Indian number in free text (snippets, AI Overview, ads)."""
    if not text:
        return []
    found: dict[str, Phone] = {}
    for match in phonenumbers.PhoneNumberMatcher(text, "IN", leniency=phonenumbers.Leniency.VALID):
        phone = _from_parsed(match.number, match.raw_string)
        if phone:
            found.setdefault(phone.key, phone)
    for m in _BFSI_1600.finditer(text):
        phone = parse(m.group(0))
        if phone:
            found.setdefault(phone.key, phone)
    return list(found.values())
