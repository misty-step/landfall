#!/usr/bin/env python3
"""Update an existing GitHub Release body with synthesized user-facing notes."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import requests


WHATS_NEW_RE = re.compile(
    r"^## What's New\b.*?(?=^##\s+|\Z)",
    flags=re.MULTILINE | re.DOTALL,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepend synthesized release notes under a What's New section."
    )
    parser.add_argument("--github-token", required=True, help="GitHub token with repo write access.")
    parser.add_argument("--repository", required=True, help="GitHub repository in owner/repo format.")
    parser.add_argument("--tag", required=True, help="Release tag to update.")
    parser.add_argument("--notes-file", required=True, help="Path to synthesized notes markdown file.")
    parser.add_argument("--api-base-url", default="https://api.github.com", help="GitHub API base URL.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    return parser.parse_args()


def read_notes(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def strip_existing_whats_new(body: str) -> str:
    cleaned = WHATS_NEW_RE.sub("", body, count=1).strip()
    return cleaned


def github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }


def fetch_release(
    api_base_url: str,
    repository: str,
    tag: str,
    headers: dict[str, str],
    timeout: int,
) -> dict:
    url = f"{api_base_url}/repos/{repository}/releases/tags/{tag}"
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def update_release_body(
    api_base_url: str,
    repository: str,
    release_id: int,
    body: str,
    headers: dict[str, str],
    timeout: int,
) -> None:
    url = f"{api_base_url}/repos/{repository}/releases/{release_id}"
    response = requests.patch(url, headers=headers, json={"body": body}, timeout=timeout)
    response.raise_for_status()


def compose_release_body(synth_notes: str, existing_body: str) -> str:
    technical_body = strip_existing_whats_new(existing_body) if existing_body else ""
    sections = [f"## What's New\n\n{synth_notes.strip()}"]
    if technical_body:
        sections.append(technical_body)
    return "\n\n".join(section.strip() for section in sections if section.strip()).strip() + "\n"


def main() -> int:
    args = parse_args()
    headers = github_headers(args.github_token)

    try:
        synthesized_notes = read_notes(Path(args.notes_file))
    except OSError as exc:
        print(f"Error reading notes file: {exc}", file=sys.stderr)
        return 1

    if not synthesized_notes:
        print("Error: synthesized notes file is empty", file=sys.stderr)
        return 1

    try:
        release = fetch_release(
            api_base_url=args.api_base_url,
            repository=args.repository,
            tag=args.tag,
            headers=headers,
            timeout=args.timeout,
        )
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        text = exc.response.text if exc.response is not None else str(exc)
        print(f"GitHub API HTTP error when fetching release ({status}): {text}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"GitHub API request failed when fetching release: {exc}", file=sys.stderr)
        return 1

    release_id = release.get("id")
    if not isinstance(release_id, int):
        print("Error: release response did not include numeric id", file=sys.stderr)
        return 1

    existing_body = release.get("body") or ""
    updated_body = compose_release_body(synthesized_notes, existing_body)

    try:
        update_release_body(
            api_base_url=args.api_base_url,
            repository=args.repository,
            release_id=release_id,
            body=updated_body,
            headers=headers,
            timeout=args.timeout,
        )
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        text = exc.response.text if exc.response is not None else str(exc)
        print(f"GitHub API HTTP error when updating release ({status}): {text}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"GitHub API request failed when updating release: {exc}", file=sys.stderr)
        return 1

    print(f"Updated release '{args.tag}' in '{args.repository}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
