"""The web app: a JSON API over the committed snapshots, and the React app (frontend/) that presents it.

The React app is built once with Vite into kalaana/static/app/ and committed, so running Kal Aana
needs no Node and no API key:

    kalaana serve        (or: uvicorn kalaana.web:app --port 8000)

    /                        the app (the chat, the map, report cards, office pages, the method)
    /api/chat                POST {"messages": [...]}: the chat's reply as server-sent events (text, cards, done);
                             nothing stored, the conversation lives in the visitor's browser
    /api/overview            totals, each office type's headline, map points, every office
    /api/office/<id>         one office: snapshot fields, verdict, story card, evidence trail
    /api/story/<id>?service=&applied=   the story card for one office (with the visitor's own wait, if given)
    /api/office/<id>/complaint?service=&applied=&number=   a complaint letter about a late service
    /api/ask                 POST {"text": ...}: a citizen's problem in their own words, read into an office,
                             a service and a date, and answered from the snapshot (nothing stored)
    /api/method              the review classifier's precision and recall, computed from the labelled sets
    /api/snapshot?office_type=rto|subregistrar|passport    the whole snapshot for one office type
    /api/docs                these endpoints, documented (the page loads its viewer, Scalar, from a CDN, so it needs
                             internet; the JSON endpoints and /api/openapi.json do not)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final

from fastapi import FastAPI, HTTPException, Path as PathParam, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse

from pydantic import BaseModel, Field

from . import ask, chat, reader, views

log = logging.getLogger("kalaana.web")
BUILD: Final = Path(__file__).resolve().parent / "static" / "app"

DESCRIPTION: Final = """What Bengaluru's public offices promise (their own phone numbers, and the working days the law gives
them for each service) against what citizens find on Google: Maps listings, Google's AI answers, Bing Maps and reviews,
collected through 628 SerpApi searches. Every page of [kal-aana.gradestone.in](https://kal-aana.gradestone.in) is drawn
from these endpoints.

- **No key, no sign-in.** The data endpoints are read-only and answer from the committed snapshot (data as of
  October 8, 2026), so they cost nothing and never call SerpApi.
- **Office ids** look like `rto-ka05`, `sro-jayanagara` or `psk-lalbagh`; `/api/overview` lists every one.
- **The chat** streams server-sent events. When a model answers, each visitor gets 20 questions per 10 minutes, and
  live searches are rationed separately; a busy limit returns 429.
- **Nothing is stored.** Questions and conversations are not kept or logged.
- **For AI assistants**, the same tools run as an MCP server: `https://kalaana-mcp.gradestone.in/mcp`.

Code and setup: [github.com/tahcin/kal-aana](https://github.com/tahcin/kal-aana)."""

TAGS: Final = [
    {"name": "Data", "description": "Read-only views of the snapshot: every office, one office in full, the method's "
                                    "accuracy figures, and the raw snapshot."},
    {"name": "Citizen tools", "description": "A citizen's own case: their wait against the legal limit, and a complaint "
                                             "letter addressed to the right officer. Nothing is stored."},
    {"name": "Chat", "description": "The chat behind the home page: a reply streamed as server-sent events, and the "
                                    "simpler ask box that reads a problem into an office, a service and a date."},
]

app = FastAPI(title="Kal Aana API", version="0.1.0", description=DESCRIPTION, openapi_tags=TAGS,
              docs_url=None, redoc_url=None, openapi_url="/api/openapi.json",
              servers=[{"url": "https://kalaana-api.gradestone.in", "description": "The live API"},
                       {"url": "/", "description": "This server"}],
              license_info={"name": "MIT", "url": "https://github.com/tahcin/kal-aana/blob/main/LICENSE"},
              contact={"name": "Kal Aana on GitHub", "url": "https://github.com/tahcin/kal-aana"})
# When the pages are hosted apart from the API (Cloudflare), their origins are listed here so browsers may call it.
if origins := [o.strip() for o in os.getenv("KALAANA_CORS", "").split(",") if o.strip()]:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

# The reference page: Scalar, themed in the site's colours, reading /api/openapi.json. Pinned to a release, from a CDN.
DOCS_PAGE: Final = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kal Aana API</title><link rel="icon" type="image/svg+xml" href="/favicon.svg">
<style>
  :root { --scalar-font: "Inter", system-ui, sans-serif; }
  .light-mode { --scalar-background-1: #f8f3ea; --scalar-background-2: #fffdf9; --scalar-background-3: #efe7d9;
    --scalar-color-1: #1c1530; --scalar-color-2: #3f3555; --scalar-color-3: #6b6178; --scalar-color-accent: #5a3fc0;
    --scalar-border-color: #e6dccb; --scalar-button-1: #5a3fc0; --scalar-button-1-color: #ffffff; --scalar-button-1-hover: #7b5fe0; }
</style></head>
<body><div id="app"></div>
<script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.72.0"></script>
<script>
  Scalar.createApiReference("#app", {
    url: "/api/openapi.json", theme: "none", forceDarkModeState: "light", hideDarkModeToggle: true, defaultOpenAllTags: true,
    showDeveloperTools: "never", agent: { disabled: true }, mcp: { disabled: true }, telemetry: false,
    metaData: { title: "Kal Aana API" },
  });
</script></body></html>"""


@app.get("/api/docs", include_in_schema=False)
def docs() -> HTMLResponse:
    return HTMLResponse(DOCS_PAGE)


@app.exception_handler(views.NotFound)
def not_found(_: Request, error: views.NotFound) -> JSONResponse:
    return JSONResponse({"detail": str(error)}, status_code=404)


class Question(BaseModel):
    text: str = Field(max_length=ask.MAX_CHARS, description="The citizen's problem in their own words, in English, Hindi or Kannada.",
                      examples=["Applied for my learner's licence at RTO South 3 weeks ago, still waiting"])


ASK_LIMIT: Final = 20  # questions per visitor per 10 minutes, when any model reads them
LIVE_LIMIT: Final = 5  # live SerpApi searches per visitor per 10 minutes (each costs a credit; repeats are free)
_searched: dict[str, deque[float]] = defaultdict(deque)
_asked: dict[str, deque[float]] = defaultdict(deque)
# Behind a Cloudflare Tunnel every request arrives from 127.0.0.1, so the visitor is the address Cloudflare reports.
# Trusted only when KALAANA_PROXY=cloudflare (the server then listens on 127.0.0.1, reachable only through the tunnel).
PROXY: Final = os.getenv("KALAANA_PROXY", "")
# A ceiling on model-read questions per day (IST) across all visitors; 0 means none (the default for a local run).
DAILY_QUESTIONS: Final = int(os.getenv("KALAANA_DAILY_QUESTIONS", "0") or 0)
_today: dict[str, int] = {}
IST: Final = timezone(timedelta(hours=5, minutes=30))


def _visitor(request: Request) -> str:
    if PROXY == "cloudflare" and (ip := request.headers.get("cf-connecting-ip")):
        return ip
    return request.client.host if request.client else "?"


def _limit(request: Request) -> None:
    """When any model reads the questions (someone's API key or GPU pays), each visitor gets ASK_LIMIT per 10 minutes,
    within the daily ceiling. Only the rules, which cost nothing, are unlimited."""
    if reader.configured() not in ("", "rules"):
        now = time.monotonic()
        if len(_asked) > 10_000:  # forget visitors with no question in the last 10 minutes
            for host in [h for h, q in _asked.items() if not q or now - q[-1] > 600]:
                del _asked[host]
        seen = _asked[_visitor(request)]
        while seen and now - seen[0] > 600:
            seen.popleft()
        if len(seen) >= ASK_LIMIT:
            raise HTTPException(429, "Too many questions for now. Try again in a few minutes.")
        day = datetime.now(IST).date().isoformat()
        if DAILY_QUESTIONS and _today.get(day, 0) >= DAILY_QUESTIONS:
            raise HTTPException(429, "Kal Aana has answered all the questions it can for today. Try again tomorrow.")
        seen.append(now)
        if day not in _today:  # a new day: forget yesterday's count
            _today.clear()
        _today[day] = _today.get(day, 0) + 1


@app.post("/api/ask", tags=["Chat"], summary="Answer a problem from the saved data", responses={429: {"description": "This visitor has asked too often for now, or the day's questions are used up."}})
def ask_endpoint(question: Question, request: Request) -> dict[str, Any]:
    """Read a citizen's problem in their own words and answer from the snapshot. Kal Aana stores and logs none of it."""
    _limit(request)
    return ask.answer(question.text)


class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$", description="Who said it: `user` or `assistant`.")
    content: str = Field(max_length=4000, description="The words; an earlier reply is sent back as its text and card note.")


class Conversation(BaseModel):
    messages: list[Turn] = Field(min_length=1, max_length=200,  # only the last few are read (chat.MAX_TURNS)
                                 description="The conversation so far, oldest first, ending with the citizen's message.",
                                 examples=[[{"role": "user", "content": "How do I reach the Jayanagar sub-registrar office?"}]])


@app.post("/api/chat", tags=["Chat"], summary="The chat's reply, streamed", responses={
    200: {"description": "Server-sent events, one JSON object per `data:` line: `status`, `text`, `card`, then `done`.",
          "content": {"text/event-stream": {"example": 'data: {"type": "status", "text": "Finding the office"}\n\n'
                                                       'data: {"type": "card", "card": {"kind": "numbers"}}\n\n'
                                                       'data: {"type": "done", "by": "rules", "memory": ""}\n\n'}}},
    429: {"description": "This visitor has asked too often for now, or the day's questions are used up."}})
def chat_endpoint(conversation: Conversation, request: Request) -> StreamingResponse:
    """The chat's reply as server-sent events: `status` (what it's checking), `text` (the model's words, with any
    number no tool returned withheld), `card` (built from the snapshot), then `done` (which reader answered).
    Kal Aana stores and logs nothing the visitor writes; with a model reader, the conversation is sent to that
    model's API to write the reply."""
    _limit(request)
    messages = [t.model_dump() for t in conversation.messages]
    try:
        chat._history(messages)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None

    visitor = _visitor(request)

    def live_quota() -> bool:
        now, seen = time.monotonic(), _searched[visitor]
        while seen and now - seen[0] > 600:
            seen.popleft()
        if len(seen) >= LIVE_LIMIT:
            return False
        seen.append(now)
        return True

    def events() -> Any:
        try:
            for event in chat.reply(messages, live_quota=live_quota):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception:  # never leak details (or a key) into the page; the log gets the trace, never the messages
            log.exception("Chat reply failed")
            yield f"data: {json.dumps({'type': 'error', 'text': 'Something went wrong. Try again.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'by': 'none', 'memory': ''})}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@app.get("/api/overview", tags=["Data"], summary="Every office, with totals and map points")
def overview() -> dict[str, Any]:
    """Totals across all offices, each office type's headline finding and search counts by engine, one row per office
    (its official number, what Google Maps shows, its listing score, reviews), map points, and listings that share a
    number. The home page, report cards and map all start here."""
    types = {t: views.load(views.CITY, t) for t in views.office_types()}
    return {
        "totals": views.totals(),
        "types": {t: {"profile": d["profile"], "headline": d["headline"], "searches": d["searches"], "rules": d["rules"],
                      "searches_by_engine": d["searches_by_engine"], "as_of": d["as_of"],
                      "lookalikes": d.get("lookalikes", [])} for t, d in types.items()},
        "offices": [{"id": o["id"], "label": views.label(o), "code": o["code"], "type": t, "type_label": d["profile"]["short"],
                     "maps": views.maps_status(o), "ai": views.ai_status(o), "score": o["reach"]["score"],
                     "official": (o["official_phones"] or [{}])[0].get("display", ""),
                     "phone": (o["listing"] or {}).get("phone_display", ""), "unclaimed": bool((o["listing"] or {}).get("unclaimed")),
                     "reviews": (o["listing"] or {}).get("reviews", 0), "sampled": o["sampled"], "checked": o["citizen_checked"],
                     "enough_evidence": o["enough_evidence"], "problem_reviews": o["problem_reviews"],
                     "window_reviews": o["window_reviews"], "breaches": len(o["breaches"])}
                    for t, d in types.items() for o in d["offices"]],
        "points": views.map_points(),
        "links": views.shared_links(),
    }


@app.get("/api/story/{office_id}", tags=["Citizen tools"], summary="An office's story, with the citizen's own wait", responses={404: {"description": "No office with that id."}})
def story(office_id: str = PathParam(description="An office id from `/api/overview`.", examples=["rto-ka05"]), service: str = Query("", description="A service id from the office type's time limits, e.g. `learners-licence`.", examples=["learners-licence"]),
          applied: str = Query("", description="When the citizen applied, YYYY-MM-DD.", examples=["2026-09-18"])) -> dict[str, Any]:
    """The story card for one office. With `service` (and `applied`, YYYY-MM-DD), it also carries the visitor's own
    wait against that service's legal limit; nothing is stored."""
    data, o = views.find_office(office_id)
    card = views.story_card(o, data)
    yours = views.your_wait(data, service, applied) if service else None
    if yours:
        card["yours"] = yours
        name = re.sub(r"\s*\([^)]*\)", "", yours["service"]).lower()
        card["takeaways"] = {**card["takeaways"], "clock": (
            f"So you've waited about {yours['elapsed']} working days on your application ({name}); {yours['allows']} {yours['limit']}."
            if yours["elapsed"] is not None else f"So for your application ({name}), {yours['allows']} {yours['limit']}.")}
    return card


@app.get("/api/office/{office_id}", tags=["Data"], summary="One office in full", responses={404: {"description": "No office with that id."}})
def office(office_id: str = PathParam(description="An office id from `/api/overview`.", examples=["rto-ka05"])) -> dict[str, Any]:
    """Everything known about one office: its directory entry and time limits, its Google Maps listing and listing
    score, what Google's AI Overview and AI Mode and Bing Maps showed, the reviews read and quotes by issue, possible
    statutory breaches, listings named like it, and every SerpApi search behind the page (with its search ID)."""
    data, o = views.find_office(office_id)
    return {
        "office": o, "card": views.story_card(o, data), "maps": views.maps_status(o), "ai": views.ai_status(o),
        "profile": data["profile"], "timelines": data["timelines"], "appeals": data["appeals"], "helpline": data["helpline"],
        "sweep": data["sweep"], "rules": data["rules"], "as_of": data["as_of"], "type_searches": data["searches"],
        "mode": views.mode_status(o), "bing": views.bing_status(o), "grievance": data.get("grievance"),
        "lookalikes": views.nearby_lookalikes(o, data), "lookalikes_total": len(data.get("lookalikes", [])),
    }


@app.get("/api/office/{office_id}/complaint", tags=["Citizen tools"], summary="A complaint letter about a late service", responses={404: {"description": "No office with that id."}})
def complaint(office_id: str = PathParam(description="An office id from `/api/overview`.", examples=["rto-ka05"]), service: str = Query("", description="A service id from the office type's time limits, e.g. `learners-licence`.", examples=["learners-licence"]),
              applied: str = Query("", description="When the citizen applied, YYYY-MM-DD.", examples=["2026-09-18"]),
              number: str = Query("", description="The application number, if the citizen has one.")) -> dict[str, Any]:
    """A draft letter to the officer the law names, counting the working days since `applied` against the service's
    limit, with the evidence and caveats. Kal Aana sends nothing: the citizen reads, edits and sends it."""
    return views.complaint(office_id, service, applied, number)


@app.get("/api/method", tags=["Data"], summary="How accurate the review reader is")
def method() -> dict[str, Any]:
    """The review classifier's precision and recall per issue, computed live from the hand-labelled sets, and the
    comparison with a small local model."""
    return views.method()


@app.get("/api/snapshot", tags=["Data"], summary="The raw snapshot for one office type", responses={404: {"description": "No snapshot for that office type."}})
def api_snapshot(office_type: str = Query("rto", description="`rto`, `subregistrar` or `passport`.", examples=["rto"])) -> dict[str, Any]:
    """The whole committed snapshot for one office type, as the pages and the MCP server read it: offices, official
    data, evidence and search IDs. Review quotes are masked."""
    if office_type not in views.office_types():
        raise HTTPException(404, f"No snapshot for {office_type}. Available: {', '.join(views.office_types())}")
    return views.load(views.CITY, office_type)


def _trim(value: Any, depth: int = 0) -> Any:
    """A response cut down for the reference page: one item per list, long text shortened, deep nesting elided."""
    if isinstance(value, dict):
        return {k: _trim(v, depth + 1) for k, v in value.items()} if depth < 4 else "{…}"
    if isinstance(value, list):
        return [_trim(v, depth + 1) for v in value[:1]]
    if isinstance(value, str) and len(value) > 160:
        return value[:160] + "…"
    return value


def _openapi() -> dict[str, Any]:
    """The schema, with a real (trimmed) response from the snapshot attached to each read-only endpoint, built once on
    first request, so the examples always match what the API returns."""
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes,
                         tags=app.openapi_tags, servers=app.servers, license_info=app.license_info, contact=app.contact)
    examples = {"/api/overview": overview, "/api/office/{office_id}": lambda: office("rto-ka05"), "/api/method": method,
                "/api/story/{office_id}": lambda: story("rto-ka05", "learners-licence", ""),
                "/api/snapshot": lambda: api_snapshot("passport")}
    for path, make in examples.items():
        try:
            body = schema["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]
            body["examples"] = {"snapshot": {"summary": "A real response, shortened", "value": _trim(make())}}
        except Exception:  # documentation must never stop the API
            log.warning("No example for %s", path)
    app.openapi_schema = schema
    return schema


app.openapi = _openapi  # type: ignore[method-assign]


@app.api_route("/api", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/api/{rest:path}", methods=["GET", "HEAD"], include_in_schema=False)
def api_unknown(rest: str = "") -> JSONResponse:
    return JSONResponse({"detail": f"No API endpoint /api/{rest}. See /api/docs."}, status_code=404)


@app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
def spa(path: str = "") -> FileResponse:
    """A built file if one exists at that path. A path with a file extension that doesn't exist is a real 404
    (a missing script or icon must not come back as HTML); any other path gets the app's index.html, which routes on the client."""
    target = (BUILD / path).resolve()
    if path and target.is_file() and BUILD in target.parents:
        return FileResponse(target, headers={"Cache-Control": "public, max-age=31536000, immutable"} if path.startswith("assets/") else None)
    if Path(path).suffix:
        raise HTTPException(404, f"No file {path}")
    index = BUILD / "index.html"
    if not index.exists():
        raise HTTPException(503, "The app isn't built. Run: cd frontend && pnpm install && pnpm build")
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
