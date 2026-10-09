"""The local-LLM reading, with Ollama's HTTP API replaced by canned answers."""

import json
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from kalaana import refine


def answer(labels: list[dict[str, str]]) -> dict[str, Any]:
    """What Ollama's /api/chat returns: the model's JSON as a string in message.content."""
    return {"message": {"content": json.dumps({"labels": labels})}}


REVIEW = {"review_id": "r1", "rating": 1.0, "text": "No one picks up the phone. They asked 2000 bribe.", "text_original": ""}


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(refine, "REFINED_DIR", tmp_path)
    return tmp_path


def test_quotes_must_be_verbatim(monkeypatch: pytest.MonkeyPatch, cache: Path) -> None:
    sent: dict[str, Any] = {}

    def post(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        sent.update(payload)
        return answer([{"category": "unreachable", "quote": "no one picks up the  phone"},
                       {"category": "bribe", "quote": "demanded a bribe of 5000"},  # not in the review: invented
                       {"category": "made_up", "quote": "phone"}])

    monkeypatch.setattr(refine, "post", post)
    reading = refine.read_review(REVIEW, "test-model")
    assert reading.labels == {"unreachable": "no one picks up the  phone"}
    assert [r["category"] for r in reading.rejected] == ["bribe", "made_up"]
    assert sent["format"] == refine.SCHEMA and sent["options"]["temperature"] == 0
    assert "<review>" in sent["messages"][1]["content"]  # the review travels as delimited data


def test_readings_are_cached_and_resumed(monkeypatch: pytest.MonkeyPatch, cache: Path) -> None:
    calls = []
    monkeypatch.setattr(refine, "post", lambda url, payload, timeout: calls.append(1) or answer([]))
    refine.run([REVIEW], "test-model", progress=False)
    refine.run([REVIEW], "test-model", progress=False)
    assert len(calls) == 1 and refine.load_cache("test-model")["r1"].labels == {}


def test_missing_model_and_server(monkeypatch: pytest.MonkeyPatch, cache: Path) -> None:
    def not_found(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        raise urllib.error.HTTPError(url, 404, "model not found", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(refine, "post", not_found)
    with pytest.raises(refine.OllamaUnavailable, match="ollama pull"):
        refine.read_review(REVIEW, "missing-model")

    def refuse(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        raise urllib.error.URLError(ConnectionRefusedError())

    monkeypatch.setattr(refine, "post", refuse)
    with pytest.raises(refine.OllamaUnavailable, match="brew services start ollama"):
        refine.read_review(REVIEW, "any-model")


def test_predictor_combines_with_the_lexicon(monkeypatch: pytest.MonkeyPatch, cache: Path) -> None:
    monkeypatch.setattr(refine, "post", lambda url, payload, timeout: answer([{"category": "staff", "quote": "No one picks up"}]))
    refine.run([REVIEW], "test-model", progress=False)
    row = {**REVIEW, "n": 1}
    assert refine.predictor("test-model")(row) == {"staff"}
    assert {"staff", "unreachable", "bribe"} <= refine.predictor("test-model", combine=True)(row)


def test_post_speaks_json_over_http() -> None:
    """The one function that touches the network, against a real local HTTP server."""
    received: list[Any] = []

    class Ollama(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            body = json.dumps(answer([])).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Ollama)
    threading.Thread(target=server.handle_request, daemon=True).start()
    try:
        reply = refine.post(f"http://127.0.0.1:{server.server_port}/api/chat", {"model": "m"}, timeout=5)
    finally:
        server.server_close()
    assert received == [{"model": "m"}] and reply == answer([])
