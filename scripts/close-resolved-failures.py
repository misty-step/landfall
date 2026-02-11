#!/usr/bin/env python3
"""Close stale synthesis failure issues after a successful synthesis."""

from __future__ import annotations

import argparse
import logging
import re
from typing import Any

import requests

from shared import configure_logging, log_event, request_with_retry


REPOSITORY_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
FAILURE_TITLE_PREFIX = "[Landfall] Synthesis failed for "
LOGGER = logging.getLogger("landfall.close_resolved_failures")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Close open synthesis failure issues after a successful synthesis."
    )
    parser.add_argument("--github-token", required=True, help="GitHub token with issues write access.")
    parser.add_argument("--repository", required=True, help="GitHub repository in owner/repo format.")
    parser.add_argument("--release-tag", required=True, help="Release tag that succeeded.")
    parser.add_argument("--api-base-url", default="https://api.github.com", help="GitHub API base URL.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Number of retries for retryable HTTP failures (default: 2).",
    )
    parser.add_argument(
        "--retry-backoff",
        type=float,
        default=1.0,
        help="Base backoff seconds between retries (default: 1.0).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Structured log verbosity written to stderr.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.github_token or not args.github_token.strip():
        raise ValueError("github-token must be non-empty")
    if not args.repository or not REPOSITORY_RE.match(args.repository):
        raise ValueError("repository must match owner/repo")
    if not args.release_tag or not args.release_tag.strip():
        raise ValueError("release-tag must be non-empty")
    if args.timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    if args.retries < 0:
        raise ValueError("retries cannot be negative")
    if args.retry_backoff < 0:
        raise ValueError("retry-backoff cannot be negative")
    if not args.api_base_url.startswith(("http://", "https://")):
        raise ValueError("api-base-url must start with http:// or https://")


def github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }


def find_open_failure_issues(
    api_base_url: str,
    repository: str,
    headers: dict[str, str],
    timeout: int,
    retries: int,
    retry_backoff: float,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Return open issues whose title starts with the Landfall failure prefix."""
    url = f"{api_base_url}/repos/{repository}/issues"
    params = {"state": "open", "per_page": 100}

    created_session = session is None
    http = session or requests.Session()
    try:
        response = request_with_retry(
            LOGGER,
            http,
            "GET",
            url,
            headers=headers,
            params=params,
            timeout=timeout,
            retries=retries,
            retry_backoff=retry_backoff,
        )
        all_issues = response.json()
    finally:
        if created_session:
            http.close()

    return [
        issue
        for issue in all_issues
        if isinstance(issue, dict)
        and isinstance(issue.get("title"), str)
        and issue["title"].startswith(FAILURE_TITLE_PREFIX)
    ]


def close_issue_with_comment(
    api_base_url: str,
    repository: str,
    issue_number: int,
    release_tag: str,
    headers: dict[str, str],
    timeout: int,
    retries: int,
    retry_backoff: float,
    session: requests.Session | None = None,
) -> None:
    """Add a resolution comment and close the issue."""
    created_session = session is None
    http = session or requests.Session()
    try:
        comment_url = f"{api_base_url}/repos/{repository}/issues/{issue_number}/comments"
        comment_body = (
            f"Closing: synthesis succeeded for {release_tag}. "
            "This failure has been resolved."
        )
        request_with_retry(
            LOGGER,
            http,
            "POST",
            comment_url,
            headers=headers,
            json={"body": comment_body},
            timeout=timeout,
            retries=retries,
            retry_backoff=retry_backoff,
        )

        issue_url = f"{api_base_url}/repos/{repository}/issues/{issue_number}"
        request_with_retry(
            LOGGER,
            http,
            "PATCH",
            issue_url,
            headers=headers,
            json={"state": "closed", "state_reason": "completed"},
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

    headers = github_headers(args.github_token)

    try:
        issues = find_open_failure_issues(
            api_base_url=args.api_base_url,
            repository=args.repository,
            headers=headers,
            timeout=args.timeout,
            retries=args.retries,
            retry_backoff=args.retry_backoff,
        )
    except (requests.HTTPError, requests.RequestException) as exc:
        log_event(LOGGER, logging.WARNING, "list_issues_failed", error=str(exc))
        return 0

    if not issues:
        log_event(LOGGER, logging.INFO, "no_open_failure_issues")
        return 0

    closed_count = 0
    for issue in issues:
        issue_number = issue["number"]
        issue_title = issue["title"]
        try:
            close_issue_with_comment(
                api_base_url=args.api_base_url,
                repository=args.repository,
                issue_number=issue_number,
                release_tag=args.release_tag,
                headers=headers,
                timeout=args.timeout,
                retries=args.retries,
                retry_backoff=args.retry_backoff,
            )
            closed_count += 1
            log_event(
                LOGGER,
                logging.INFO,
                "failure_issue_closed",
                issue_number=issue_number,
                title=issue_title,
            )
        except (requests.HTTPError, requests.RequestException) as exc:
            log_event(
                LOGGER,
                logging.WARNING,
                "close_issue_failed",
                issue_number=issue_number,
                error=str(exc),
            )

    log_event(
        LOGGER,
        logging.INFO,
        "resolved_failures_summary",
        closed=closed_count,
        total=len(issues),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
