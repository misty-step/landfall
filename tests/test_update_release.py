from __future__ import annotations

import sys
from pathlib import Path

import requests


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error


class FakeSession:
    def __init__(self, outcomes: list[object]):
        self.outcomes = outcomes
        self.calls: list[dict] = []

    def request(self, *, method: str, url: str, timeout: int, **kwargs):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "timeout": timeout,
                "kwargs": kwargs,
            }
        )
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self) -> None:
        return None


def build_http_error(status_code: int, text: str) -> requests.HTTPError:
    response = FakeResponse(status_code=status_code, payload={}, text=text)
    error = requests.HTTPError(f"HTTP {status_code}")
    error.response = response
    return error


def test_compose_release_body_replaces_existing_whats_new(update_release):
    synthesized = "## Improvements\n- Faster startup."
    existing = "## What's New\n\nOld copy.\n\n## Technical Changes\n- internal item"

    body = update_release.compose_release_body(synthesized, existing)

    assert body.startswith("## What's New")
    assert "Old copy." not in body
    assert "## Technical Changes" in body


def test_fetch_release_retries_on_retryable_status(update_release, monkeypatch):
    monkeypatch.setattr(sys.modules["shared"].time, "sleep", lambda *_: None)
    session = FakeSession(
        [
            FakeResponse(status_code=502, payload={"message": "bad gateway"}, text="bad gateway"),
            FakeResponse(status_code=200, payload={"id": 42, "body": "existing"}),
        ]
    )

    release = update_release.fetch_release(
        api_base_url="https://api.github.test",
        repository="octo/example",
        tag="v1.2.3",
        headers={"Authorization": "Bearer token"},
        timeout=5,
        retries=1,
        retry_backoff=0.0,
        session=session,
    )

    assert release["id"] == 42
    assert len(session.calls) == 2


def test_main_returns_error_when_release_tag_missing(update_release, monkeypatch, tmp_path: Path):
    notes_file = tmp_path / "notes.md"
    notes_file.write_text("## Improvements\n- Better UX.", encoding="utf-8")

    def fake_fetch_release(**_kwargs):
        raise build_http_error(404, "release tag not found")

    monkeypatch.setattr(update_release, "fetch_release", fake_fetch_release)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "update-release.py",
            "--github-token",
            "token",
            "--repository",
            "octo/example",
            "--tag",
            "v9.9.9",
            "--notes-file",
            str(notes_file),
        ],
    )

    assert update_release.main() == 1


def test_main_returns_error_on_api_timeout(update_release, monkeypatch, tmp_path: Path):
    notes_file = tmp_path / "notes.md"
    notes_file.write_text("## Improvements\n- Better UX.", encoding="utf-8")

    def fake_fetch_release(**_kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(update_release, "fetch_release", fake_fetch_release)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "update-release.py",
            "--github-token",
            "token",
            "--repository",
            "octo/example",
            "--tag",
            "v1.0.0",
            "--notes-file",
            str(notes_file),
        ],
    )

    assert update_release.main() == 1


def test_main_successfully_updates_release(update_release, monkeypatch, tmp_path: Path):
    notes_file = tmp_path / "notes.md"
    notes_file.write_text("## Improvements\n- Faster startup.", encoding="utf-8")
    captured: dict[str, str] = {}

    def fake_fetch_release(**_kwargs):
        return {"id": 99, "body": "## Technical Changes\n- patch"}

    def fake_update_release_body(**kwargs):
        captured["body"] = kwargs["body"]

    monkeypatch.setattr(update_release, "fetch_release", fake_fetch_release)
    monkeypatch.setattr(update_release, "update_release_body", fake_update_release_body)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "update-release.py",
            "--github-token",
            "token",
            "--repository",
            "octo/example",
            "--tag",
            "v1.0.0",
            "--notes-file",
            str(notes_file),
        ],
    )

    assert update_release.main() == 0
    assert captured["body"].startswith("## What's New")
    assert "## Technical Changes" in captured["body"]
