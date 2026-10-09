"""The chat's agent over an OpenAI-compatible endpoint, against a fake server on this machine that streams canned
server-sent events (no paid calls)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from kalaana import chat, live, reader, web
from test_chat import TODAY, events

IS_LOCAL = reader.is_local
QUESTION = [{"role": "user", "content": "learner's licence at KA-05 applied 3 weeks ago"}]


def text(content: str, finish: str | None = None) -> dict[str, Any]:
    return {"choices": [{"index": 0, "delta": {"content": content}, "finish_reason": finish}]}


def tool_piece(index: int, arguments: str, name: str = "", id: str = "") -> dict[str, Any]:
    piece: dict[str, Any] = {"index": index, "function": {"arguments": arguments}}
    if name:
        piece |= {"id": id, "type": "function", "function": {"name": name, "arguments": arguments}}
    return {"choices": [{"index": 0, "delta": {"tool_calls": [piece]}, "finish_reason": None}]}


def finish(reason: str) -> dict[str, Any]:
    return {"choices": [{"index": 0, "delta": {}, "finish_reason": reason}]}


USAGE: dict[str, Any] = {"choices": [], "usage": {"prompt_tokens": 1000, "completion_tokens": 100, "total_tokens": 1100}}


class FakeServer:
    """Answers each POST with the next canned reply: a list of chunks to stream, or an HTTP error status."""

    def __init__(self) -> None:
        self.replies: list[list[dict[str, Any]] | int] = []
        self.requests: list[dict[str, Any]] = []
        self.headers: list[dict[str, str]] = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                server.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                server.headers.append(dict(self.headers))
                reply = server.replies.pop(0)
                if isinstance(reply, int):
                    self.send_response(reply)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"error": {"message": "this model does not support tools"}}')
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                for chunk in reply:
                    self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")

            def log_message(self, *_: Any) -> None:
                return None

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Any:
    fake = FakeServer()
    monkeypatch.setenv("KALAANA_READER", "openai")
    monkeypatch.setenv("OPENAI_BASE_URL", fake.url)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("KALAANA_MODEL", "some-model")
    monkeypatch.delenv("KALAANA_CHAT_MODEL", raising=False)
    monkeypatch.setattr(reader, "SPEND_FILE", tmp_path / "spend.json")
    monkeypatch.setattr(reader, "_ledger_failed", False)
    monkeypatch.setattr(reader, "is_local", lambda url: False)  # count it as a paid cloud API
    monkeypatch.setattr(live, "is_cached", lambda tool, args: False)
    yield fake
    fake.httpd.shutdown()


def check_wait_split() -> list[dict[str, Any]]:
    """A check_wait call whose arguments arrive in three pieces, after a line of text."""
    return [text("Let me check."), tool_piece(0, '{"office_id": "rto-ka05", "serv', name="check_wait", id="call_1"),
            tool_piece(0, 'ice": "learners-licence", '), tool_piece(0, '"applied": "2026-09-17"}'), finish("tool_calls"), USAGE]


def search(n: int, query: str) -> dict[str, Any]:
    return tool_piece(n, json.dumps({"query": query, "official_only": True}), name="search_web", id=f"s{n}")


def test_a_tool_call_split_across_chunks_runs_and_an_invented_number_is_withheld(server: FakeServer) -> None:
    server.replies = [check_wait_split(),
                      [text("That's past the limit; call 99"), text("99 999 999 or the office."), finish("stop"), USAGE]]
    got = events(chat.reply(QUESTION, TODAY))
    words = "".join(e["text"] for e in got if e["type"] == "text")
    assert [e["card"]["kind"] for e in got if e["type"] == "card"] == ["wait"]
    assert chat.WITHHELD in words and "99 999" not in words
    assert got[-1]["by"] == "some-model (OpenAI-compatible API)" and got[-1]["withheld"] == 1
    assert "check_wait(office_id=rto-ka05" in got[-1]["memory"]
    first, second = server.requests
    assert first["stream"] and first["stream_options"] == {"include_usage": True} and first["messages"][0]["role"] == "system"
    assert first["tools"][0]["type"] == "function" and first["tools"][0]["function"]["parameters"]["additionalProperties"] is False
    assert server.headers[0]["Authorization"] == "Bearer test-key"
    # The assembled call went back with its result, in the OpenAI format.
    call, result = second["messages"][-2], second["messages"][-1]
    assert json.loads(call["tool_calls"][0]["function"]["arguments"]) == {"office_id": "rto-ka05", "service": "learners-licence",
                                                                          "applied": "2026-09-17"}
    assert result["role"] == "tool" and result["tool_call_id"] == "call_1" and "working_days_since" in result["content"]
    spent = reader.spent()
    assert spent["calls"] == 2 and spent["usd"] == pytest.approx(2 * (1000 * 10 + 100 * 50) / 1_000_000)  # unknown model: top price


def test_a_search_for_what_the_saved_data_holds_is_refused(server: FakeServer, monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[Any] = []
    monkeypatch.setitem(chat.TOOL_FUNCTIONS, "search_web", lambda **kw: ran.append(kw) or ({"kind": "search"}, {}))
    server.replies = [[search(0, "RTO KA-05 phone number"), finish("tool_calls"), USAGE], [text("Use the office's own number."), USAGE]]
    events(chat.reply(QUESTION, TODAY))
    assert not ran and "saved data already covers" in server.requests[1]["messages"][-1]["content"]


def test_no_more_than_two_live_searches_in_a_reply(server: FakeServer, monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[Any] = []
    monkeypatch.setitem(chat.TOOL_FUNCTIONS, "search_web", lambda **kw: ran.append(kw) or (None, {"results": []}))
    server.replies = [[search(0, "learner's licence documents"), search(1, "learner's licence fees"), search(2, "learner's licence form"),
                       finish("tool_calls"), USAGE], [text("Here's what I found."), USAGE]]
    got = events(chat.reply(QUESTION, TODAY))
    assert len(ran) == chat.MAX_LIVE_PER_REPLY
    assert "No more live searches" in server.requests[1]["messages"][-1]["content"]
    assert [m["tool_call_id"] for m in server.requests[1]["messages"] if m["role"] == "tool"] == ["s0", "s1", "s2"]
    assert got[-1]["type"] == "done"


def test_running_out_of_tokens_ends_the_reply(server: FakeServer) -> None:
    server.replies = [[text("Your licence"), text(" is"), finish("length"), USAGE]]
    got = events(chat.reply(QUESTION, TODAY))
    words = "".join(e["text"] for e in got if e["type"] == "text")
    assert words.endswith("I can't go further with that one.") and len(server.requests) == 1 and got[-1]["type"] == "done"


def test_a_call_with_no_usage_reported_is_counted_at_the_most_it_could_cost(server: FakeServer) -> None:
    server.replies = [[text("Hello."), finish("stop")]]
    events(chat.reply(QUESTION, TODAY))
    assert reader.spent()["usd"] >= chat.MAX_TOKENS * 50 / 1_000_000


def test_a_model_without_tool_calling_falls_back_to_the_rules(server: FakeServer) -> None:
    server.replies = [400]
    got = events(chat.reply(QUESTION, TODAY))
    assert got[-1]["by"] == "rules" and "wasn't available" in got[-1]["note"]
    assert "wait" in [e["card"]["kind"] for e in got if e["type"] == "card"]


def test_a_spent_budget_falls_back_to_the_rules_without_calling(server: FakeServer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KALAANA_ASK_BUDGET_USD", "0")
    got = events(chat.reply(QUESTION, TODAY))
    assert not server.requests and got[-1]["by"] == "rules" and "budget" in got[-1]["note"]


def test_a_server_on_this_machine_is_free(server: FakeServer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reader, "is_local", IS_LOCAL)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("KALAANA_MODEL", "gemma3:4b")
    monkeypatch.setenv("KALAANA_ASK_BUDGET_USD", "0")  # no budget, yet a local model still answers
    server.replies = [[text("Hello."), finish("stop")]]
    got = events(chat.reply(QUESTION, TODAY))
    assert got[-1]["by"] == "gemma3:4b (OpenAI-compatible API)" and "Authorization" not in server.headers[0]
    assert reader.spent()["calls"] == 0


def test_a_cloud_endpoint_needs_a_model_and_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.com/v1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("KALAANA_MODEL", raising=False)
    with pytest.raises(reader.ReaderError, match="KALAANA_MODEL"):
        reader.openai_model()
    with pytest.raises(reader.ReaderError, match="OPENAI_API_KEY"):
        reader.openai_endpoint()
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.anthropic.com/v1/")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
    assert reader.openai_endpoint() == ("https://api.anthropic.com/v1/chat/completions", {"Authorization": "Bearer a-key"})


@pytest.mark.parametrize("kind", ["openai", "anthropic", "ollama", "llamacpp"])
def test_every_model_reader_is_rate_limited(kind: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(web.reader, "configured", lambda: kind)
    monkeypatch.setattr(web, "PROXY", "")
    monkeypatch.setattr(web, "_asked", web.defaultdict(web.deque))
    monkeypatch.setattr(web, "_today", {})
    request = type("R", (), {"headers": {}, "client": type("C", (), {"host": "192.0.2.9"})()})()
    for _ in range(web.ASK_LIMIT):
        web._limit(request)
    with pytest.raises(web.HTTPException):
        web._limit(request)


@pytest.mark.parametrize(("url", "local"), [
    ("http://localhost:11434/v1/chat/completions", True), ("http://127.0.0.1:8080/v1", True), ("http://192.168.1.20:11434/v1", True),
    ("http://10.0.0.5/v1", True), ("http://gpu-box.local:11434/v1", True), ("https://api.openai.com/v1", False),
    ("https://api.anthropic.com/v1/", False), ("http://8.8.8.8/v1", False)])
def test_a_model_on_this_machine_or_the_local_network_is_free(url: str, local: bool) -> None:
    assert IS_LOCAL(url) is local
