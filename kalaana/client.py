"""SerpApi client with an on-disk cache and a hard search budget.

The free plan allows 250 searches a month, so every response is cached by its
parameters and a run refuses to spend more than KALAANA_SEARCH_BUDGET fresh searches.
Without an API key the client runs in demo mode and serves only cached results. The
`serpapi` package is only needed for live searches (pip install "kal-aana[live]").
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .paths import DATA_DIR

load_dotenv()

CACHE_DIR = Path(os.getenv("KALAANA_CACHE_DIR", DATA_DIR / "cache"))


class CacheMiss(RuntimeError):
    """Raised in demo mode when a search isn't in the cache."""


class BudgetExceeded(RuntimeError):
    """Raised when a run would spend more fresh searches than allowed."""


class SearchError(RuntimeError):
    """A SerpApi request failed. The message never contains the API key."""


@dataclass(frozen=True)
class SearchRecord:
    """One search a run asked for: what it cost and where its evidence lives."""

    engine: str
    params: dict[str, Any]
    cached: bool
    search_id: str
    json_endpoint: str  # SerpApi's archived copy (kept 31 days), the evidence link

    @property
    def label(self) -> str:
        return self.params.get("q") or self.params.get("query") or self.params.get("data_id") or self.params.get("place_id", "")


def _redact(text: str, key: str) -> str:
    text = re.sub(r"api_key=[^&\s]+", "api_key=***", text)
    return text.replace(key, "***") if key else text


REQUEST_TIMEOUT_S = 90  # an AI Mode answer can take a minute; a hung request shouldn't stall a whole run


class SearchClient:
    def __init__(self, api_key: str | None = None, budget: int | None = None, cache_dir: Path = CACHE_DIR,
                 dry_run: bool = False, timeout: float = REQUEST_TIMEOUT_S):
        self.api_key = api_key if api_key is not None else os.getenv("SERPAPI_API_KEY", "").strip()
        self.budget = budget if budget is not None else int(os.getenv("KALAANA_SEARCH_BUDGET", "40"))
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.spent = 0
        self.cache_hits = 0
        self.log: list[SearchRecord] = []
        # Dry run: serve the cache, and log (but don't make) every search that would cost a credit.
        self.dry_run = dry_run
        self._client: Any = None  # serpapi.Client, made on the first live search
        self.timeout = timeout

    @property
    def demo_mode(self) -> bool:
        return not self.api_key

    def _serpapi(self) -> Any:
        if self._client is None:
            try:
                import serpapi
            except ImportError:
                raise SearchError('Live searches need the serpapi package: pip install -e ".[live]"') from None
            self._client = serpapi.Client(api_key=self.api_key, timeout=self.timeout)
        return self._client

    @staticmethod
    def _safe(params: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in params.items() if k != "api_key"}

    @staticmethod
    def cache_key(params: dict[str, Any]) -> str:
        clean = {k: v for k, v in sorted(params.items()) if k != "api_key" and v is not None}
        return hashlib.sha1(json.dumps(clean, sort_keys=True).encode()).hexdigest()

    def _path(self, params: dict[str, Any]) -> Path:
        return self.cache_dir / f"{params.get('engine', 'google')}-{self.cache_key(params)}.json"

    def search(self, params: dict[str, Any], refresh: bool = False) -> dict[str, Any]:
        path = self._path(params)
        if path.exists() and not refresh:
            self.cache_hits += 1
            result = json.loads(path.read_text(encoding="utf-8"))
            self._record(params, result, cached=True)
            return result
        if self.dry_run:
            self.log.append(SearchRecord(params.get("engine", "google"), self._safe(params), False, "", ""))
            return {}
        if self.demo_mode:
            raise CacheMiss(f"Not cached and no SERPAPI_API_KEY set: {self._safe(params)}")
        if self.spent >= self.budget:
            raise BudgetExceeded(f"Search budget of {self.budget} used up for this run")
        try:
            result = dict(self._serpapi().search(params))
        except SearchError:
            raise
        except Exception as e:  # serpapi.HTTPError, timeouts, connection errors
            response = getattr(e, "response", None)
            status = getattr(response, "status_code", "")
            hint = " (check SERPAPI_API_KEY in .env)" if status == 401 else ""
            try:
                detail = f" ({response.json()['error']})"
            except Exception:  # no response, or not SerpApi's JSON error shape
                detail = ""
            message = f"SerpApi request failed {status}{hint}{detail}: {params.get('engine')} {params.get('q', '')}"
            raise SearchError(_redact(message, self.api_key)) from None
        self.spent += 1
        result.setdefault("kalaana", {})["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        # Written whole or not at all, so a reader in another process never sees half a file.
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)
        self._record(params, result, cached=False)
        return result

    def _record(self, params: dict[str, Any], result: dict[str, Any], cached: bool) -> None:
        meta = result.get("search_metadata", {})
        self.log.append(SearchRecord(params.get("engine", "google"), self._safe(params), cached, meta.get("id", ""), meta.get("json_endpoint", "")))

    def usage(self) -> str:
        mode = "demo (cache only)" if self.demo_mode else f"live, {self.spent}/{self.budget} fresh searches"
        return f"{mode}, {self.cache_hits} cache hits"
