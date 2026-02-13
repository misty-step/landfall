#!/usr/bin/env python3
"""Write synthesized release notes to portable artifact files."""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import sys
from pathlib import Path
from typing import Any

from notes_render import markdown_to_html_fragment, markdown_to_plaintext


LOGGER = logging.getLogger("landfall.write_artifacts")


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stderr)


def log_event(level: int, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    LOGGER.log(level, json.dumps(payload, sort_keys=True, default=str))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write synthesized release notes to file and JSON artifacts."
    )
    parser.add_argument("--notes-file", required=True, help="Path to synthesized notes markdown file.")
    parser.add_argument("--version", required=True, help="Release tag or version string.")
    parser.add_argument(
        "--output-file",
        default="",
        help="Output markdown path. Supports {version} placeholder.",
    )
    parser.add_argument(
        "--output-text-file",
        default="",
        help="Output plaintext path (email/blog ready). Supports {version} placeholder.",
    )
    parser.add_argument(
        "--output-html-file",
        default="",
        help="Output HTML fragment path. Supports {version} placeholder.",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Output JSON file path. Appends release entry to a JSON array.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Structured log verbosity written to stderr.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.notes_file or not args.notes_file.strip():
        raise ValueError("notes-file must be non-empty")
    if not args.version or not args.version.strip():
        raise ValueError("version must be non-empty")


def read_notes(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def ensure_parent_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def interpolate_output_path(path_template: str, version: str) -> Path:
    return Path(path_template.replace("{version}", version))


def write_notes_file(notes: str, output_path_template: str, version: str) -> Path:
    destination = interpolate_output_path(output_path_template, version)
    ensure_parent_directory(destination)
    destination.write_text(notes, encoding="utf-8")
    log_event(logging.INFO, "notes_file_written", path=str(destination))
    return destination


def normalize_json_version(version: str) -> str:
    if version.startswith("v"):
        return version[1:]
    return version


def load_json_array(path: Path) -> list[Any]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("output-json root must be a JSON array")
    return payload


def append_json_entry(
    notes: str,
    version: str,
    output_json_path: str,
    *,
    notes_plaintext: str | None = None,
    notes_html: str | None = None,
    today: datetime.date | None = None,
) -> Path:
    destination = Path(output_json_path)
    entries = load_json_array(destination)

    derived_plaintext = notes_plaintext if notes_plaintext is not None else markdown_to_plaintext(notes)
    derived_html = notes_html if notes_html is not None else markdown_to_html_fragment(notes)

    entries.append(
        {
            "version": normalize_json_version(version),
            "date": (today or datetime.date.today()).isoformat(),
            "notes": notes,
            "notes_plaintext": derived_plaintext,
            "notes_html": derived_html,
        }
    )
    ensure_parent_directory(destination)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=2)
        handle.write("\n")
    log_event(logging.INFO, "notes_json_written", path=str(destination), entries=len(entries))
    return destination


def main() -> int:
    args = parse_args()
    configure_logging(args.log_level)

    try:
        validate_args(args)
    except ValueError as exc:
        log_event(logging.ERROR, "invalid_input", error=str(exc))
        return 1

    version = args.version.strip()
    output_file = args.output_file.strip()
    output_text_file = args.output_text_file.strip()
    output_html_file = args.output_html_file.strip()
    output_json = args.output_json.strip()

    try:
        notes = read_notes(Path(args.notes_file))
    except OSError as exc:
        log_event(logging.ERROR, "notes_read_failed", path=args.notes_file, error=str(exc))
        return 1

    if not notes:
        log_event(logging.ERROR, "empty_notes_file", path=args.notes_file)
        return 1

    notes_plaintext = markdown_to_plaintext(notes)
    notes_html = markdown_to_html_fragment(notes)

    print(notes)

    if output_file:
        try:
            write_notes_file(notes=notes, output_path_template=output_file, version=version)
        except OSError as exc:
            log_event(logging.ERROR, "notes_file_write_failed", path=output_file, error=str(exc))
            return 1

    if output_text_file:
        try:
            write_notes_file(notes=notes_plaintext, output_path_template=output_text_file, version=version)
        except OSError as exc:
            log_event(logging.ERROR, "notes_file_write_failed", path=output_text_file, error=str(exc))
            return 1

    if output_html_file:
        try:
            write_notes_file(notes=notes_html, output_path_template=output_html_file, version=version)
        except OSError as exc:
            log_event(logging.ERROR, "notes_file_write_failed", path=output_html_file, error=str(exc))
            return 1

    if output_json:
        try:
            append_json_entry(
                notes=notes,
                version=version,
                output_json_path=output_json,
                notes_plaintext=notes_plaintext,
                notes_html=notes_html,
            )
        except json.JSONDecodeError as exc:
            log_event(logging.ERROR, "notes_json_parse_failed", path=output_json, error=str(exc))
            return 1
        except ValueError as exc:
            log_event(logging.ERROR, "notes_json_invalid", path=output_json, error=str(exc))
            return 1
        except OSError as exc:
            log_event(logging.ERROR, "notes_json_write_failed", path=output_json, error=str(exc))
            return 1

    if not output_file and not output_text_file and not output_html_file and not output_json:
        log_event(logging.INFO, "artifacts_noop")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
