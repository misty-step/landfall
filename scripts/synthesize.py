#!/usr/bin/env python3
"""Generate user-facing release notes from technical changelog content."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import requests


DEFAULT_API_URL = "https://api.moonshot.ai/v1/chat/completions"
SECTION_HEADING_RE = re.compile(r"^##\s+.+$", re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synthesize user-facing release notes with Moonshot/Kimi."
    )
    parser.add_argument("--api-key", required=True, help="Moonshot API key.")
    parser.add_argument(
        "--model", default="kimi-k2.5", help="Moonshot model ID (default: kimi-k2.5)."
    )
    parser.add_argument(
        "--api-url", default=DEFAULT_API_URL, help="Moonshot chat completions endpoint."
    )
    parser.add_argument(
        "--prompt-template",
        required=True,
        help="Path to prompt template markdown file.",
    )
    parser.add_argument(
        "--changelog-file",
        default="CHANGELOG.md",
        help="Path to markdown changelog.",
    )
    parser.add_argument(
        "--technical-changelog-file",
        help="Optional path to raw technical changelog text.",
    )
    parser.add_argument(
        "--product-name",
        help="Product name injected into the prompt template.",
    )
    parser.add_argument(
        "--version",
        help="Version or tag used to locate a changelog section.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds.",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def normalize_version(version: str) -> str:
    return version.strip().lstrip("v")


def extract_release_section(changelog_text: str, version: str | None) -> str:
    headings = list(SECTION_HEADING_RE.finditer(changelog_text))
    if not headings:
        return changelog_text.strip()

    target_index = 0
    if version:
        normalized = normalize_version(version).lower()
        for index, match in enumerate(headings):
            heading = match.group(0).lower()
            if normalized in heading or f"v{normalized}" in heading:
                target_index = index
                break
        else:
            print(
                f"Warning: version '{version}' not found in changelog headings. "
                "Using latest section.",
                file=sys.stderr,
            )

    start = headings[target_index].start()
    if target_index + 1 < len(headings):
        end = headings[target_index + 1].start()
    else:
        end = len(changelog_text)
    return changelog_text[start:end].strip()


def render_prompt(template_text: str, product_name: str, version: str, technical: str) -> str:
    return (
        template_text.replace("{{PRODUCT_NAME}}", product_name)
        .replace("{{VERSION}}", version)
        .replace("{{TECHNICAL_CHANGELOG}}", technical)
    )


def infer_product_name(explicit_name: str | None) -> str:
    if explicit_name:
        return explicit_name
    repository = os.getenv("GITHUB_REPOSITORY", "")
    if "/" in repository:
        return repository.split("/", 1)[1]
    return "this product"


def synthesize_notes(
    api_url: str,
    api_key: str,
    model: str,
    prompt: str,
    timeout: int,
) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": "You rewrite technical release notes into user-facing product notes.",
            },
            {"role": "user", "content": prompt},
        ],
    }

    response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    body = response.json()

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Moonshot response did not include choices[0].message.content") from exc

    notes = content.strip()
    if not notes:
        raise RuntimeError("Moonshot returned empty synthesized notes")
    return notes


def main() -> int:
    args = parse_args()
    template_path = Path(args.prompt_template)

    try:
        template_text = read_text(template_path)
    except OSError as exc:
        print(f"Error reading prompt template '{template_path}': {exc}", file=sys.stderr)
        return 1

    try:
        if args.technical_changelog_file:
            technical_text = read_text(Path(args.technical_changelog_file))
        else:
            changelog_text = read_text(Path(args.changelog_file))
            technical_text = extract_release_section(changelog_text, args.version)
    except OSError as exc:
        print(f"Error reading changelog content: {exc}", file=sys.stderr)
        return 1

    if not technical_text:
        print("Error: technical changelog text is empty", file=sys.stderr)
        return 1

    product_name = infer_product_name(args.product_name)
    version = args.version or "latest"
    prompt = render_prompt(template_text, product_name, version, technical_text)

    try:
        synthesized = synthesize_notes(
            api_url=args.api_url,
            api_key=args.api_key,
            model=args.model,
            prompt=prompt,
            timeout=args.timeout,
        )
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        text = exc.response.text if exc.response is not None else str(exc)
        print(f"Moonshot API HTTP error ({status}): {text}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Moonshot API request failed: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Synthesis error: {exc}", file=sys.stderr)
        return 1

    print(synthesized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
