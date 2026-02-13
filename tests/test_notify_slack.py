from __future__ import annotations

import argparse
from unittest.mock import patch

import pytest

from conftest import FakeResponse, load_script_module


@pytest.fixture(scope="session")
def notify_slack():
    return load_script_module("landfall_notify_slack", "scripts/notify-slack.py")


# --- validate_args ---


def test_validate_args_accepts_valid_inputs(notify_slack):
    args = argparse.Namespace(
        slack_webhook_url="https://hooks.slack.com/services/T000/B000/XXX",
        version="v1.2.3",
        repository="octo/example",
        release_url="https://github.com/octo/example/releases/tag/v1.2.3",
        notes_file="notes.md",
        timeout=10,
        retries=2,
        retry_backoff=1.0,
        log_level="INFO",
    )
    notify_slack.validate_args(args)


def test_validate_args_rejects_empty_slack_webhook_url(notify_slack):
    args = argparse.Namespace(
        slack_webhook_url="",
        version="v1.2.3",
        repository="octo/example",
        release_url="https://github.com/octo/example/releases/tag/v1.2.3",
        notes_file="notes.md",
        timeout=10,
        retries=2,
        retry_backoff=1.0,
        log_level="INFO",
    )
    with pytest.raises(ValueError, match="slack-webhook-url must be non-empty"):
        notify_slack.validate_args(args)


def test_validate_args_rejects_non_http_slack_webhook_url(notify_slack):
    args = argparse.Namespace(
        slack_webhook_url="ftp://bad",
        version="v1.2.3",
        repository="octo/example",
        release_url="https://github.com/octo/example/releases/tag/v1.2.3",
        notes_file="notes.md",
        timeout=10,
        retries=2,
        retry_backoff=1.0,
        log_level="INFO",
    )
    with pytest.raises(ValueError, match="slack-webhook-url must start with http"):
        notify_slack.validate_args(args)


def test_validate_args_rejects_empty_version(notify_slack):
    args = argparse.Namespace(
        slack_webhook_url="https://hooks.slack.com/services/T000/B000/XXX",
        version="  ",
        repository="octo/example",
        release_url="https://github.com/octo/example/releases/tag/v1.2.3",
        notes_file="notes.md",
        timeout=10,
        retries=2,
        retry_backoff=1.0,
        log_level="INFO",
    )
    with pytest.raises(ValueError, match="version must be non-empty"):
        notify_slack.validate_args(args)


# --- markdown conversion ---


def test_md_inline_to_slack_mrkdwn_converts_bold(notify_slack):
    assert notify_slack.md_inline_to_slack_mrkdwn("**Bold** item") == "*Bold* item"


def test_md_inline_to_slack_mrkdwn_converts_link(notify_slack):
    assert notify_slack.md_inline_to_slack_mrkdwn("[Docs](https://example.com)") == "<https://example.com|Docs>"


def test_parse_notes_sections_extracts_headings_and_bullets(notify_slack):
    notes = "## New Features\n- One\n- Two\n\n## Bug Fixes\n- Fixed it"
    sections = notify_slack.parse_notes_sections(notes)
    assert sections == [("New Features", ["One", "Two"]), ("Bug Fixes", ["Fixed it"])]


# --- build_slack_payload ---


def test_build_slack_payload_has_blocks(notify_slack):
    payload = notify_slack.build_slack_payload(
        version="v1.2.3",
        repository="octo/example",
        release_url="https://github.com/octo/example/releases/tag/v1.2.3",
        notes_markdown="## New Features\n- **Bold** [Docs](https://example.com)",
    )
    assert payload["text"]
    assert "blocks" in payload
    assert payload["blocks"][0]["type"] == "header"
    assert payload["blocks"][-1]["type"] == "context"


# --- send_slack_webhook ---


def test_send_slack_webhook_posts_payload(notify_slack, request_session_factory):
    session = request_session_factory(outcomes=[FakeResponse(status_code=200, text="OK")])
    payload = {"text": "hello", "blocks": []}

    notify_slack.send_slack_webhook(
        slack_webhook_url="https://hooks.slack.com/services/T000/B000/XXX",
        payload=payload,
        timeout=10,
        retries=0,
        retry_backoff=0.0,
        session=session,
    )

    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["method"] == "POST"
    assert call["url"].startswith("https://hooks.slack.com/")
    assert call["kwargs"]["headers"]["Content-Type"] == "application/json"
    assert call["kwargs"]["json"] == payload


# --- main integration ---


def test_main_returns_0_on_success(notify_slack, tmp_path, request_session_factory):
    notes_file = tmp_path / "notes.md"
    notes_file.write_text("## New Features\n- Feature A")

    session = request_session_factory(outcomes=[FakeResponse(status_code=200, text="OK")])

    with patch.object(notify_slack, "parse_args", return_value=argparse.Namespace(
        slack_webhook_url="https://hooks.slack.com/services/T000/B000/XXX",
        version="v1.2.3",
        repository="octo/example",
        release_url="https://github.com/octo/example/releases/tag/v1.2.3",
        notes_file=str(notes_file),
        timeout=10,
        retries=0,
        retry_backoff=0.0,
        log_level="INFO",
    )), patch("requests.Session", return_value=session):
        result = notify_slack.main()

    assert result == 0
    assert len(session.calls) == 1


def test_main_returns_1_on_missing_notes_file(notify_slack, tmp_path):
    with patch.object(notify_slack, "parse_args", return_value=argparse.Namespace(
        slack_webhook_url="https://hooks.slack.com/services/T000/B000/XXX",
        version="v1.2.3",
        repository="octo/example",
        release_url="https://github.com/octo/example/releases/tag/v1.2.3",
        notes_file=str(tmp_path / "missing.md"),
        timeout=10,
        retries=0,
        retry_backoff=0.0,
        log_level="INFO",
    )):
        result = notify_slack.main()

    assert result == 1


def test_main_returns_1_on_empty_notes_file(notify_slack, tmp_path):
    notes_file = tmp_path / "empty.md"
    notes_file.write_text("   ")

    with patch.object(notify_slack, "parse_args", return_value=argparse.Namespace(
        slack_webhook_url="https://hooks.slack.com/services/T000/B000/XXX",
        version="v1.2.3",
        repository="octo/example",
        release_url="https://github.com/octo/example/releases/tag/v1.2.3",
        notes_file=str(notes_file),
        timeout=10,
        retries=0,
        retry_backoff=0.0,
        log_level="INFO",
    )):
        result = notify_slack.main()

    assert result == 1


def test_main_returns_1_on_http_error(notify_slack, tmp_path, request_session_factory):
    notes_file = tmp_path / "notes.md"
    notes_file.write_text("## Bug Fixes\n- Fixed it")

    session = request_session_factory(outcomes=[FakeResponse(status_code=400, text="bad")])

    with patch.object(notify_slack, "parse_args", return_value=argparse.Namespace(
        slack_webhook_url="https://hooks.slack.com/services/T000/B000/XXX",
        version="v1.2.3",
        repository="octo/example",
        release_url="https://github.com/octo/example/releases/tag/v1.2.3",
        notes_file=str(notes_file),
        timeout=10,
        retries=0,
        retry_backoff=0.0,
        log_level="INFO",
    )), patch("requests.Session", return_value=session):
        result = notify_slack.main()

    assert result == 1

