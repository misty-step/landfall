from __future__ import annotations

import sys
from pathlib import Path

import pytest
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


def test_render_prompt_replaces_placeholders(synthesize):
    template = "Name={{PRODUCT_NAME}} Version={{VERSION}}\n\n{{TECHNICAL_CHANGELOG}}"
    rendered = synthesize.render_prompt(
        template_text=template,
        product_name="Landfall",
        version="1.2.3",
        technical="### Fixes\n- improved stability",
    )
    assert rendered == "Name=Landfall Version=1.2.3\n\n### Fixes\n- improved stability"


def test_extract_release_section_falls_back_to_latest_when_version_missing(synthesize):
    changelog = (
        "## 1.2.0\n\n- newest change\n\n"
        "## 1.1.0\n\n- older change\n"
    )
    section = synthesize.extract_release_section(changelog, "2.0.0")
    assert section.startswith("## 1.2.0")
    assert "- newest change" in section


def test_synthesize_notes_retries_retryable_status(synthesize, monkeypatch):
    monkeypatch.setattr(sys.modules["shared"].time, "sleep", lambda *_: None)
    session = FakeSession(
        [
            FakeResponse(status_code=500, payload={"error": "temporary"}, text="temporary"),
            FakeResponse(
                status_code=200,
                payload={"choices": [{"message": {"content": "## Improvements\n- Faster sync."}}]},
            ),
        ]
    )

    notes = synthesize.synthesize_notes(
        api_url="https://api.example.test/chat/completions",
        api_key="secret",
        model="test-model",
        prompt="prompt text",
        timeout=5,
        retries=1,
        retry_backoff=0.0,
        session=session,
    )

    assert notes == "## Improvements\n- Faster sync."
    assert len(session.calls) == 2


def test_synthesize_notes_timeout_raises_after_retries(synthesize, monkeypatch):
    monkeypatch.setattr(sys.modules["shared"].time, "sleep", lambda *_: None)
    session = FakeSession([requests.Timeout("first timeout"), requests.Timeout("second timeout")])

    with pytest.raises(requests.Timeout):
        synthesize.synthesize_notes(
            api_url="https://api.example.test/chat/completions",
            api_key="secret",
            model="test-model",
            prompt="prompt text",
            timeout=5,
            retries=1,
            retry_backoff=0.0,
            session=session,
        )

    assert len(session.calls) == 2


def test_main_returns_error_for_empty_changelog(synthesize, monkeypatch, tmp_path: Path):
    template_file = tmp_path / "prompt.md"
    template_file.write_text(
        "Release for {{PRODUCT_NAME}} {{VERSION}}\n\n{{TECHNICAL_CHANGELOG}}",
        encoding="utf-8",
    )
    changelog_file = tmp_path / "CHANGELOG.md"
    changelog_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "synthesize.py",
            "--api-key",
            "secret",
            "--prompt-template",
            str(template_file),
            "--changelog-file",
            str(changelog_file),
            "--timeout",
            "5",
        ],
    )

    assert synthesize.main() == 1
