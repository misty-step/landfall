from __future__ import annotations

import pytest
import requests

import healthcheck


def _make_response(status_code: int, json_data: object = None):
    class _Resp:
        def __init__(self):
            self.status_code = status_code
            self._json = json_data or {}
            self.text = ""

        def json(self):
            return self._json

        def raise_for_status(self):
            if self.status_code >= 400:
                err = requests.HTTPError(f"HTTP {self.status_code}")
                err.response = self
                raise err

    return _Resp()


def test_probe_api_succeeds_with_valid_response(monkeypatch):
    def fake_retry(_logger, _session, _method, _url, **_kw):
        return _make_response(200, {"choices": [{"message": {"content": "OK"}}]})

    monkeypatch.setattr(healthcheck, "request_with_retry", fake_retry)
    healthcheck.probe_api("https://api.test/v1/chat/completions", "key", "model", 10)


def test_probe_api_raises_on_401(monkeypatch):
    def fake_retry(_logger, _session, _method, _url, **_kw):
        resp = _make_response(401)
        resp.raise_for_status()

    monkeypatch.setattr(healthcheck, "request_with_retry", fake_retry)
    with pytest.raises(requests.HTTPError):
        healthcheck.probe_api("https://api.test/v1/chat/completions", "bad", "model", 10)


def test_probe_api_raises_on_empty_content(monkeypatch):
    def fake_retry(_logger, _session, _method, _url, **_kw):
        return _make_response(200, {"choices": [{"message": {"content": "   "}}]})

    monkeypatch.setattr(healthcheck, "request_with_retry", fake_retry)
    with pytest.raises(RuntimeError, match="empty response"):
        healthcheck.probe_api("https://api.test/v1/chat/completions", "key", "model", 10)


def test_main_returns_0_on_success(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["healthcheck.py", "--api-key", "valid-key", "--model", "test"],
    )

    def fake_retry(_logger, _session, _method, _url, **_kw):
        return _make_response(200, {"choices": [{"message": {"content": "OK"}}]})

    monkeypatch.setattr(healthcheck, "request_with_retry", fake_retry)
    assert healthcheck.main() == 0


def test_main_returns_1_on_401(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["healthcheck.py", "--api-key", "bad-key", "--model", "test"],
    )

    events: list[dict] = []

    def capture_log(_logger, level, event, **fields):
        events.append({"level": level, "event": event, **fields})

    monkeypatch.setattr(healthcheck, "log_event", capture_log)

    def fake_retry(_logger, _session, _method, _url, **_kw):
        resp = _make_response(401)
        resp.raise_for_status()

    monkeypatch.setattr(healthcheck, "request_with_retry", fake_retry)
    assert healthcheck.main() == 1

    failed = [e for e in events if e["event"] == "healthcheck_failed"]
    assert len(failed) == 1
    assert failed[0]["status_code"] == 401


def test_main_returns_1_on_empty_key(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["healthcheck.py", "--api-key", "", "--model", "test"],
    )

    events: list[dict] = []

    def capture_log(_logger, level, event, **fields):
        events.append({"level": level, "event": event, **fields})

    monkeypatch.setattr(healthcheck, "log_event", capture_log)
    assert healthcheck.main() == 1

    skipped = [e for e in events if e["event"] == "healthcheck_skipped"]
    assert len(skipped) == 1
