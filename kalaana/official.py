"""Official ground truth: published office directories and statutory service timelines.

Everything here is copied from government sources into data/official/*.toml, and every
office and timeline carries the URL it came from. Loading is strict: an unknown key, a
missing field, a row without a source or a number that can't be dialled is a data error,
never something to skip quietly.
"""

from __future__ import annotations

import dataclasses
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Final

from . import phones
from .paths import DATA_DIR

OFFICIAL_DIR = DATA_DIR / "official"

LANDLINE: Final = "landline"
CUG: Final = "official mobile (CUG)"
OFFICE_MOBILE: Final = "office mobile"

# Directory column -> (label, the phone kind that column must hold). Fax lines are kept
# on the office for reference but never offered as a way to reach it.
PHONE_FIELDS: Final = {"landlines": (LANDLINE, "landline"), "cug": (CUG, "mobile"), "phones": (OFFICE_MOBILE, "mobile")}

META_KEYS: Final = frozenset({
    "office_type", "source_url", "source_name", "portal_url", "previous_version_url", "fetched", "city", "act",
    "helpline", "helpline_source", "grievance_portals", "grievance_phones", "grievance_email", "complaint_to", "complaint_email",
})
OFFICE_KEYS: Final = frozenset({
    "id", "name", "code", "kind", "group", "address", "email", "fax", "source_url", "note", "name_note",
    "published_errors", "aliases", *PHONE_FIELDS,
})
HELPLINE_KEYS: Final = frozenset({"id", "name", "phone", "hours", "source_url"})
SERVICE_KEYS: Final = frozenset({
    "id", "office_type", "name", "days", "unit", "page", "condition", "excludes", "source_url",
})

# A 6-digit PIN starting with 5 (Karnataka and Andhra/Telangana) as the last number in an address.
_PINCODE = re.compile(r"(?<!\d)(5\d{2})\s?(\d{3})(?!\d)")


class OfficialDataError(ValueError):
    """A row in data/official is malformed, unsourced or holds a number that can't be dialled."""


@dataclass(frozen=True)
class ListedPhone:
    phone: phones.Phone
    label: str  # LANDLINE | CUG | OFFICE_MOBILE


@dataclass(frozen=True)
class Office:
    id: str
    office_type: str
    name: str
    source_url: str
    kind: str = ""  # e.g. RTO, ARTO, PSK
    code: str = ""  # e.g. KA-05
    group: str = ""  # RTO division or district registrar office
    address: str = ""
    email: str = ""
    fax: str = ""
    phones: tuple[ListedPhone, ...] = ()
    notes: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()  # ours, not the source's: other spellings used on Google Maps

    @property
    def pincode(self) -> str:
        matches = _PINCODE.findall(self.address)
        return "".join(matches[-1]) if matches else ""

    @cached_property
    def phone_keys(self) -> frozenset[str]:
        return frozenset(p.phone.key for p in self.phones)


@dataclass(frozen=True)
class Timeline:
    id: str
    office_type: str
    name: str
    days: int
    source_url: str
    unit: str = "working days"
    page: int | None = None
    condition: str = ""
    excludes: str = ""

    @property
    def limit(self) -> str:
        """'7 working days', '1 working day'."""
        return f"{self.days} {self.unit[:-1] if self.days == 1 and self.unit.endswith('s') else self.unit}"

    @property
    def citation(self) -> str:
        return f"{self.source_url}#page={self.page}" if self.page else self.source_url


@dataclass(frozen=True)
class AppealChain:
    designated_officer: str
    first_appeal: str
    first_appeal_days: int
    second_appeal: str
    second_appeal_days: int


@dataclass(frozen=True)
class NationalHelpline:
    id: str
    name: str
    phone: phones.Phone
    source_url: str
    hours: str = ""


@dataclass(frozen=True)
class OfficialData:
    offices: dict[str, Office]
    timelines: dict[str, Timeline]
    appeals: dict[str, AppealChain]  # office_type -> chain
    helplines: dict[str, phones.Phone]  # office_type -> department helpline
    national: dict[str, NationalHelpline]  # phone key -> national helpline
    # office_type -> where to escalate when there is no statutory appeal (passport: the MEA's grievance channels)
    grievances: dict[str, dict[str, Any]] = dataclasses.field(default_factory=dict)

    def offices_of(self, office_type: str) -> list[Office]:
        return [o for o in self.offices.values() if o.office_type == office_type]

    def timelines_for(self, office_type: str) -> list[Timeline]:
        return [t for t in self.timelines.values() if t.office_type == office_type]


def _check_keys(row: Mapping[str, Any], allowed: frozenset[str], where: str) -> None:
    unknown = set(row) - allowed
    if unknown:
        raise OfficialDataError(f"{where}: unknown key(s) {', '.join(sorted(unknown))}")


def _parse_phone(raw: str, where: str) -> phones.Phone:
    phone = phones.parse(raw)
    if phone is None:
        raise OfficialDataError(f"{where}: {raw!r} is not a valid Indian number")
    return phone


def _listed_phones(row: Mapping[str, Any], where: str) -> tuple[ListedPhone, ...]:
    listed = []
    for field_name, (label, kind) in PHONE_FIELDS.items():
        for raw in row.get(field_name, []):
            phone = _parse_phone(raw, f"{where} {field_name}")
            if phone.kind == "fixed_or_mobile":  # the directory column settles what the digits can't
                phone = dataclasses.replace(phone, kind=kind)
            if phone.kind != kind:
                raise OfficialDataError(f"{where}: {raw!r} in {field_name} is a {phone.kind} number, expected {kind}")
            listed.append(ListedPhone(phone, label))
    return tuple(listed)


def _office(row: Mapping[str, Any], meta: Mapping[str, Any], where: str) -> Office:
    _check_keys(row, OFFICE_KEYS, where)
    source = row.get("source_url") or meta.get("source_url")
    if not source:
        raise OfficialDataError(f"{where}: no source_url")
    if "office_type" not in meta:
        raise OfficialDataError(f"{where}: [meta] has no office_type")
    notes = [row[k] for k in ("note", "name_note") if row.get(k)] + list(row.get("published_errors", []))
    try:
        return Office(
            id=row["id"],
            office_type=meta["office_type"],
            name=row["name"],
            source_url=source,
            kind=row.get("kind", ""),
            code=row.get("code", ""),
            group=row.get("group", ""),
            address=row.get("address", ""),
            email=row.get("email", ""),
            fax=row.get("fax", ""),
            phones=_listed_phones(row, where),
            notes=tuple(notes),
            aliases=tuple(row.get("aliases", [])),
        )
    except KeyError as e:
        raise OfficialDataError(f"{where}: missing {e.args[0]}") from None


def _timeline(row: Mapping[str, Any], meta: Mapping[str, Any], where: str) -> Timeline:
    _check_keys(row, SERVICE_KEYS, where)
    source = row.get("source_url") or meta.get("source_url")
    if not source:
        raise OfficialDataError(f"{where}: no source_url")
    days, page = row.get("days"), row.get("page")
    if type(days) is not int or days <= 0:
        raise OfficialDataError(f"{where}: days must be a positive integer, got {days!r}")
    if page is not None and (type(page) is not int or page <= 0):
        raise OfficialDataError(f"{where}: page must be a positive integer, got {page!r}")
    try:
        return Timeline(
            id=row["id"],
            office_type=row.get("office_type") or meta["office_type"],
            name=row["name"],
            days=days,
            source_url=source,
            unit=row.get("unit", "working days"),
            page=page,
            condition=row.get("condition", ""),
            excludes=row.get("excludes", ""),
        )
    except KeyError as e:
        raise OfficialDataError(f"{where}: missing {e.args[0]}") from None


def load(directory: Path = OFFICIAL_DIR) -> OfficialData:
    """Load and validate every data/official/*.toml file. Raises OfficialDataError on bad data."""
    data = OfficialData(offices={}, timelines={}, appeals={}, helplines={}, national={})
    for path in sorted(Path(directory).glob("*.toml")):
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
        meta = doc.get("meta", {})
        _check_keys(meta, META_KEYS, f"{path.name} [meta]")
        _check_keys(doc, frozenset({"meta", "office", "service", "appeals", "helpline"}), path.name)
        for row in doc.get("office", []):
            office = _office(row, meta, f"{path.name} office {row.get('id', '?')}")
            if office.id in data.offices:
                raise OfficialDataError(f"{path.name}: duplicate office id {office.id}")
            data.offices[office.id] = office
        for row in doc.get("service", []):
            timeline = _timeline(row, meta, f"{path.name} service {row.get('id', '?')}")
            if timeline.id in data.timelines:
                raise OfficialDataError(f"{path.name}: duplicate service id {timeline.id}")
            data.timelines[timeline.id] = timeline
        for office_type, chain in doc.get("appeals", {}).items():
            if office_type in data.appeals:
                raise OfficialDataError(f"{path.name}: duplicate appeals for {office_type}")
            try:
                data.appeals[office_type] = AppealChain(**chain)
            except TypeError as e:
                raise OfficialDataError(f"{path.name} appeals.{office_type}: {e}") from None
        for row in doc.get("helpline", []):
            where = f"{path.name} helpline {row.get('id', '?')}"
            _check_keys(row, HELPLINE_KEYS, where)
            try:
                line = NationalHelpline(row["id"], row["name"], _parse_phone(row["phone"], where),
                                        row.get("source_url") or meta["source_url"], row.get("hours", ""))
            except KeyError as e:
                raise OfficialDataError(f"{where}: missing {e.args[0]}") from None
            data.national[line.phone.key] = line
        if "helpline" in meta:
            data.helplines[meta["office_type"]] = _parse_phone(meta["helpline"], f"{path.name} helpline")
        if "grievance_portals" in meta:
            data.grievances[meta["office_type"]] = {
                "portals": list(meta["grievance_portals"]), "phones": list(meta.get("grievance_phones", [])),
                "email": meta.get("grievance_email", ""), "source_name": meta.get("source_name", ""),
                "complaint_to": meta.get("complaint_to", ""), "complaint_email": meta.get("complaint_email", ""),
                "source_url": meta["source_url"]}
    return data
