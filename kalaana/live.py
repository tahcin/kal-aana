"""Live SerpApi searches for the chat and the MCP server, for what the snapshot can't answer: procedures, documents,
fees, status tracking, outages ("is Sarathi down today?").

Every live search costs a SerpApi credit, so they are rationed:

    KALAANA_LIVE_TOTAL    most live searches ever (default 300), counted in data/private/live-searches.json
    KALAANA_LIVE_DAILY    most per day, IST (default 40)
    KALAANA_LIVE_RESERVE  stop when the account has this many credits left or fewer (default 50), read from SerpApi's
                          free Account API, so the credits kept for refreshing the dataset are never touched

A repeated search within the hour is served from our cache (free, and SerpApi's own cache would also not charge it);
cached searches are deleted after an hour, since a search's query comes from a visitor's message.
A search times out after TIMEOUT_S; after a timeout or a server error it is retried once, which SerpApi's own cache
usually answers at no charge. Government sites come first: Google is asked for gov.in pages (`as_sitesearch`), and a
result counts as official only when its host ends in gov.in or nic.in. Results are passed on as found, with their links; mobile numbers
that aren't in a department's directory are masked, as everywhere else.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlsplit

from . import official, views
from .client import SearchClient, SearchError
from .paths import DATA_DIR
from .redact import mask_phones
from .snapshot import official_keys

log = logging.getLogger("kalaana.live")
LEDGER: Final = DATA_DIR / "private" / "live-searches.json"  # gitignored
CACHE: Final = DATA_DIR / "cache" / "live"  # gitignored
FRESH_S: Final = 3600
TIMEOUT_S: Final = 35  # a fresh Google search took up to 23 s in testing; past this, say it failed rather than hang
RESULTS: Final = 6
LOCATION: Final = "Bengaluru,Karnataka,India"
_OFFICIAL: Final = re.compile(r"(?:[a-z0-9-]+\.)*(?:gov\.in|nic\.in)")  # matched against a whole, parsed host name
_HOST: Final = re.compile(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+")
_PHONE_LIKE: Final = re.compile(r"\+?\d(?:[\s().-]*\d){5,}")  # six or more digits, however written
SNIPPET_CHARS: Final = 300
_lock = threading.Lock()  # within one process; _ledger_lock() also locks across processes (web app and MCP server)
_account: dict[str, Any] = {"at": 0.0, "left": None}


class LiveUnavailable(RuntimeError):
    """No live search now (no key, or a budget reached); the reason is safe to show."""


def _limit(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return 0


def ledger() -> dict[str, Any]:
    try:
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
        return {"total": int(data["total"]), "days": {str(k): int(v) for k, v in data["days"].items()}}
    except FileNotFoundError:
        return {"total": 0, "days": {}}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):  # damaged: count it as spent, never as empty
        return {"total": 10**9, "days": {}}


def _save(data: dict[str, Any]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=LEDGER.parent, prefix=".live-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(data))
    os.replace(tmp, LEDGER)


def _credits_left(client: SearchClient) -> int | None:
    """Credits left on the account, from the free Account API (checked at most once a minute)."""
    if time.monotonic() - _account["at"] > 60:
        try:
            _account["left"] = int(dict(client._serpapi().account())["total_searches_left"])
        except Exception:  # unreachable: treat as unknown, and refuse below
            _account["left"] = None
        _account["at"] = time.monotonic()
    return _account["left"]


def status() -> dict[str, Any]:
    """What's left of the live-search budget (no network)."""
    data, today = ledger(), views.clock_today().isoformat()
    return {"total_used": data["total"], "total_limit": _limit("KALAANA_LIVE_TOTAL", 300),
            "today_used": data["days"].get(today, 0), "daily_limit": _limit("KALAANA_LIVE_DAILY", 40)}


@contextmanager
def _ledger_lock() -> Iterator[None]:
    """Hold the ledger for one check-and-count, across threads and processes (the web app and the MCP server share it)."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with _lock, open(LEDGER.with_suffix(".lock"), "a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _cached(path: Path) -> dict[str, Any] | None:
    try:
        if time.time() - path.stat().st_mtime < FRESH_S:
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # missing, or half written by another process: a miss
        pass
    return None


def _forget_old() -> None:
    """Delete cached live searches older than an hour: a search's query comes from a visitor's message, so it isn't kept."""
    for path in CACHE.glob("*.json"):
        try:
            if time.time() - path.stat().st_mtime >= FRESH_S:
                path.unlink()
        except OSError:  # another process got there first
            pass


def _search(params: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """(response, fresh): from our cache if under an hour old, else one rationed SerpApi search."""
    client = SearchClient(budget=1, cache_dir=CACHE, timeout=TIMEOUT_S)
    _forget_old()
    path = client._path(params)
    if (hit := _cached(path)) is not None:
        return hit, False
    if client.demo_mode:
        raise LiveUnavailable("Live search needs a SerpApi key (SERPAPI_API_KEY), so this answer uses the saved data only.")
    left = _credits_left(client)  # outside the lock: a slow Account API call mustn't hold up every search
    if left is None or left <= _limit("KALAANA_LIVE_RESERVE", 50):
        raise LiveUnavailable("Live search is paused to keep SerpApi credits in reserve, so this answer uses the saved data only.")
    with _ledger_lock():
        if (hit := _cached(path)) is not None:  # someone else just searched the same thing
            return hit, False
        data, today = ledger(), views.clock_today().isoformat()
        if data["total"] >= _limit("KALAANA_LIVE_TOTAL", 300) or data["days"].get(today, 0) >= _limit("KALAANA_LIVE_DAILY", 40):
            raise LiveUnavailable("Kal Aana's live-search allowance is used up for now, so this answer uses the saved data only.")
        # Count it before the call: an abandoned or failed request is never under-counted.
        data["total"] += 1
        data["days"][today] = data["days"].get(today, 0) + 1
        _save(data)
        _account["left"] = (_account["left"] or left) - 1
    try:
        try:
            return client.search(params, refresh=True), True
        except SearchError as e:
            if not e.retryable:
                raise
            # A timeout or a dropped connection: SerpApi usually finishes the search anyway and keeps it in its own
            # cache for an hour, where a repeat costs no credit, so one retry is quick and free.
            log.warning("Live search failed, retrying once: %s", _unquoted(e))
            return client.search(params, refresh=True), True
    except SearchError as e:
        log.warning("Live search failed: %s", _unquoted(e))
        raise LiveUnavailable("The live search failed just now, so this answer uses the saved data only.") from None


def _unquoted(error: SearchError) -> str:
    """The failure without its query: a live query comes from a visitor's message, and the log keeps no part of one.
    (The message never carries the key either: client.py redacts it.)"""
    return str(error).rsplit(": ", 1)[0]


def host(link: str) -> str:
    """The host name of an https link, or "" when the link is malformed or could disguise its host (user info, a
    backslash, whitespace, a port, characters a host can't have)."""
    try:
        parts = urlsplit(link or "")
        name = (parts.hostname or "").rstrip(".")
    except ValueError:
        return ""
    if parts.scheme != "https" or "@" in parts.netloc or ":" in parts.netloc or re.search(r"[\\\s]", link) \
            or not _HOST.fullmatch(name):
        return ""
    return name.removeprefix("www.")


def is_official(name: str) -> bool:
    return bool(name) and bool(_OFFICIAL.fullmatch(name))


def _clean(text: str, official: bool = True) -> str:
    """Tidy a result's text. A government page's text keeps directory numbers and helplines in full and masks other
    mobiles; another site's text has every phone-like number masked, so it can't put a number in front of a citizen."""
    text = re.sub(r"\s+", " ", text or "").strip()[:SNIPPET_CHARS]
    return mask_phones(text, _directory()) if official else _PHONE_LIKE.sub("[number]", text)


@lru_cache(maxsize=1)
def _directory() -> frozenset[str]:
    """Numbers that may be shown in full: every office's directory numbers and the helplines."""
    return official_keys(official.load())


def _query(query: str) -> str:
    """One spelling per query (case and spacing don't change Google's results), so repeats reuse the cached search."""
    return re.sub(r"\s+", " ", query).strip().lower()[:200]


def _web_params(query: str, official_only: bool) -> dict[str, Any]:
    params = {"engine": "google", "q": _query(query), "location": LOCATION, "gl": "in", "hl": "en", "num": 10}
    if official_only:
        params["as_sitesearch"] = "gov.in"  # a "site:" operator in the query was ignored in testing; this parameter isn't
    return params


def _news_params(query: str) -> dict[str, Any]:
    return {"engine": "google_news", "q": _query(query), "gl": "in", "hl": "en"}


def is_cached(tool: str, args: dict[str, Any]) -> bool:
    """Whether this search was made in the last hour, so answering it again costs no credit and no visitor allowance."""
    params = _web_params(str(args.get("query", "")), bool(args.get("official_only", True))) if tool == "search_web" \
        else _news_params(str(args.get("query", "")))
    return _cached(SearchClient(budget=0, cache_dir=CACHE)._path(params)) is not None


def search_web(query: str, official_only: bool = True) -> dict[str, Any]:
    """A Google search from Bengaluru. With `official_only`, Google is asked for gov.in pages only (nic.in pages, such
    as Sakala's, need `official_only=False`, and are still marked official)."""
    params = _web_params(query, official_only)
    query = params["q"]
    result, fresh = _search(params)
    meta = result.get("search_metadata", {})
    items = []
    for r in result.get("organic_results", []):
        name = host(r.get("link", ""))
        if name:
            official = is_official(name)
            items.append({"title": _clean(r.get("title", ""), official), "link": r["link"], "domain": name, "official": official,
                          "snippet": _clean(r.get("snippet", ""), official), "date": r.get("date", "")})
    # Google sometimes ignores the site filter. Government pages come first; if there are none, the other results are
    # kept (one search, not two) but marked, and `no_official` says so. Nothing else is ever marked official.
    official = [x for x in items if x["official"]]
    no_official = official_only and not official
    items = (official if official_only and official else sorted(items, key=lambda x: not x["official"]))[:RESULTS]
    return {"query": query, "official_only": official_only, "no_official": no_official, "results": items, "search_id": meta.get("id", ""),
            "searched_at": (result.get("kalaana") or {}).get("fetched_at") or meta.get("created_at", ""), "fresh": fresh}


def search_news(query: str) -> dict[str, Any]:
    """Google News for India: recent reports such as an outage or a strike."""
    params = _news_params(query)
    query = params["q"]
    result, fresh = _search(params)
    meta = result.get("search_metadata", {})
    items = []
    for r in result.get("news_results", []):
        story = r if r.get("link") else (r.get("highlight") or {})
        name = host(str(story.get("link", "")))
        if name:
            official = is_official(name)
            items.append({"title": _clean(story.get("title", ""), official), "link": story["link"], "domain": name,
                          "source": (story.get("source") or {}).get("name", ""), "date": story.get("iso_date") or story.get("date", ""),
                          "iso": bool(story.get("iso_date")), "official": official})
    items.sort(key=lambda x: (x["iso"], x["date"] if x["iso"] else ""), reverse=True)  # dated first, newest first
    return {"query": query, "results": items[:RESULTS], "search_id": meta.get("id", ""),
            "searched_at": (result.get("kalaana") or {}).get("fetched_at") or meta.get("created_at", ""), "fresh": fresh}

