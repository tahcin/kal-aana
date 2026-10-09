"""Tests never spend money: whatever .env says, the ask box and chat read with rules unless a test opts in (with a
fake client), and live SerpApi searches are off unless a test opts in (with a fake SerpApi)."""

import pytest


@pytest.fixture(autouse=True)
def no_paid_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KALAANA_READER", "rules")
    monkeypatch.setenv("KALAANA_LIVE_TOTAL", "0")
