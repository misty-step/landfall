#!/usr/bin/env python3
"""Send Slack Incoming Webhook notification for a release using Block Kit."""

from __future__ import annotations

import argparse
import datetime
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

from shared import configure_logging, log_event, request_with_retry

LOGGER = logging.getLogger("landfall.notify_slack")
REPOSITORY_RE = re.compile(r"^[^/\s]+/[^/\s]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="POST Slack release notification.")
    parser.add_argument("--slack-webhook-url", required=True, help="Slack Incoming Webhook URL.")
    parser.add_argument("--version", required=True, help="Release tag (e.g. v1.2.3).")
    parser.add_argument("--repository", required=True, help="GitHub repository (owner/repo).")
    parser.add_argument("--release-url", required=True, help="GitHub Release URL.")
    parser.add_argument("--notes-file", required=True, help="Path to synthesized notes markdown.")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout seconds.")
    parser.add_argument("--retries", type=int, default=2, help="Retry count for retryable failures.")
    parser.add_argument("--retry-backoff", type=float, default=1.0, help="Base backoff seconds.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Structured log verbosity.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.slack_webhook_url or not args.slack_webhook_url.strip():
        raise ValueError("slack-webhook-url must be non-empty")
    if not args.slack_webhook_url.startswith(("http://", "https://")):
        raise ValueError("slack-webhook-url must start with http:// or https://")
    if not args.version or not args.version.strip():
        raise ValueError("version must be non-empty")
    if not args.repository or not REPOSITORY_RE.match(args.repository):
        raise ValueError("repository must match owner/repo")
    if not args.release_url or not args.release_url.startswith(("http://", "https://")):
        raise ValueError("release-url must start with http:// or https://")
    if args.timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    if args.retries < 0:
        raise ValueError("retries cannot be negative")
    if args.retry_backoff < 0:
        raise ValueError("retry-backoff cannot be negative")


# --- Markdown conversion (minimal subset -> Slack mrkdwn) ---


def _escape_slack_text(text: str) -> str:
    # Slack recommends escaping &, <, > in text. Keep it small and predictable.
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _safe_link_href(url: str) -> str | None:
    parsed = urlparse(url.strip())
    if parsed.scheme in ("http", "https"):
        return url.strip()
    return None


def md_inline_to_slack_mrkdwn(text: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1:
                out.append(f"*{md_inline_to_slack_mrkdwn(text[i + 2:end])}*")
                i = end + 2
                continue
        if text[i] == "`":
            end = text.find("`", i + 1)
            if end != -1:
                out.append(f"`{_escape_slack_text(text[i + 1:end])}`")
                i = end + 1
                continue
        if text[i] == "[":
            mid = text.find("](", i + 1)
            if mid != -1:
                end = text.find(")", mid + 2)
                if end != -1:
                    label = text[i + 1:mid]
                    url = text[mid + 2:end]
                    href = _safe_link_href(url)
                    if href:
                        out.append(f"<{href}|{md_inline_to_slack_mrkdwn(label)}>")
                    else:
                        out.append(md_inline_to_slack_mrkdwn(label))
                    i = end + 1
                    continue
        out.append(_escape_slack_text(text[i]))
        i += 1
    return "".join(out)


SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
BULLET_RE = re.compile(r"^-\s+(.+?)\s*$")


def parse_notes_sections(markdown: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_items: list[str] = []

    def flush() -> None:
        nonlocal current_title, current_items
        if current_title and current_items:
            sections.append((current_title, current_items))
        current_title = None
        current_items = []

    for raw in markdown.splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue

        header_match = SECTION_RE.match(stripped)
        if header_match:
            flush()
            current_title = header_match.group(1).strip()
            continue

        bullet_match = BULLET_RE.match(stripped)
        if bullet_match:
            if current_title is None:
                current_title = "Updates"
            current_items.append(bullet_match.group(1).strip())
            continue

        # Continuation: keep parsing resilient to occasional wrapped lines.
        if current_items:
            current_items[-1] = f"{current_items[-1]} {stripped}"

    flush()
    return sections


def _truncate(text: str, *, max_chars: int, suffix: str = "\n_…_") -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= len(suffix):
        return text[:max_chars]
    return text[: max_chars - len(suffix)].rstrip() + suffix


def build_slack_payload(
    *,
    version: str,
    repository: str,
    release_url: str,
    notes_markdown: str,
    now: datetime.datetime | None = None,
) -> dict:
    now_utc = now or datetime.datetime.now(datetime.timezone.utc)
    timestamp = now_utc.strftime("%Y-%m-%d %H:%M UTC")

    header_text = f"{repository} {version}"
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text},
        }
    ]

    for title, items in parse_notes_sections(notes_markdown):
        lines = [f"*{_escape_slack_text(title)}*"]
        for item in items:
            lines.append(f"- {md_inline_to_slack_mrkdwn(item)}")
        section_text = _truncate("\n".join(lines), max_chars=2900)
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": section_text}})

    blocks.append(
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"<{release_url}|View release> • {timestamp}"}],
        }
    )

    return {
        "text": f"{header_text} released: {release_url}",
        "blocks": blocks,
    }


def send_slack_webhook(
    *,
    slack_webhook_url: str,
    payload: dict,
    timeout: int,
    retries: int,
    retry_backoff: float,
    session: requests.Session | None = None,
) -> None:
    created_session = session is None
    http = session or requests.Session()
    try:
        request_with_retry(
            LOGGER,
            http,
            "POST",
            slack_webhook_url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
            retries=retries,
            retry_backoff=retry_backoff,
        )
    finally:
        if created_session:
            http.close()


def main() -> int:
    args = parse_args()
    configure_logging(args.log_level)

    try:
        validate_args(args)
    except ValueError as exc:
        log_event(LOGGER, logging.ERROR, "invalid_input", error=str(exc))
        return 1

    try:
        notes = Path(args.notes_file).read_text(encoding="utf-8").strip()
    except OSError as exc:
        log_event(LOGGER, logging.ERROR, "notes_read_failed", path=args.notes_file, error=str(exc))
        return 1

    if not notes:
        log_event(LOGGER, logging.ERROR, "empty_notes_file", path=args.notes_file)
        return 1

    payload = build_slack_payload(
        version=args.version,
        repository=args.repository,
        release_url=args.release_url,
        notes_markdown=notes,
    )

    try:
        send_slack_webhook(
            slack_webhook_url=args.slack_webhook_url,
            payload=payload,
            timeout=args.timeout,
            retries=args.retries,
            retry_backoff=args.retry_backoff,
        )
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        text = exc.response.text if exc.response is not None else str(exc)
        log_event(LOGGER, logging.ERROR, "slack_http_error", status_code=status, response_body=text)
        return 1
    except requests.RequestException as exc:
        log_event(LOGGER, logging.ERROR, "slack_request_failed", error=str(exc))
        return 1

    redacted_host = urlparse(args.slack_webhook_url).hostname or "unknown"
    log_event(LOGGER, logging.INFO, "slack_sent", host=redacted_host, version=args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

