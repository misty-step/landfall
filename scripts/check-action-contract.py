#!/usr/bin/env python3
"""Validate Landfall's public action contract against documentation."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


INPUT_NAME_RE = re.compile(r"^  ([A-Za-z][A-Za-z0-9_-]*):\s*$")
PROPERTY_RE = re.compile(r"^    ([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")
LANDFALL_USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(?:\./|misty-step/landfall@)")
WITH_RE = re.compile(r"^(\s*)with:\s*$")
WITH_KEY_RE = re.compile(r"^\s*(?:#\s*)?([a-z][a-z0-9_-]*):(?:\s|$)")
README_INPUTS_HEADING = "## Inputs"
README_OUTPUTS_HEADING = "## Outputs"
CONDITIONAL_REQUIRED = frozenset({"release-tag", "llm-api-key"})


@dataclass(frozen=True)
class ActionInput:
    name: str
    required: bool
    default: str | None
    description: str

    @property
    def deprecated(self) -> bool:
        return "deprecated" in self.description.lower()


@dataclass(frozen=True)
class ReadmeInputRow:
    name: str
    required: str
    default: str
    description: str


@dataclass(frozen=True)
class UsageInput:
    path: Path
    line_number: int
    name: str


def strip_yaml_scalar(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]
    return stripped


def parse_action_inputs(path: Path) -> list[ActionInput]:
    inputs: list[ActionInput] = []
    current_name: str | None = None
    current: dict[str, str] = {}
    in_inputs = False
    multiline_key: str | None = None
    multiline_lines: list[str] = []

    def flush() -> None:
        nonlocal current_name, current
        if current_name is None:
            return
        inputs.append(
            ActionInput(
                name=current_name,
                required=current.get("required", "false").lower() == "true",
                default=current.get("default"),
                description=current.get("description", ""),
            )
        )
        current_name = None
        current = {}

    def flush_multiline() -> None:
        nonlocal multiline_key, multiline_lines
        if multiline_key is not None:
            current[multiline_key] = " ".join(line.strip() for line in multiline_lines if line.strip())
        multiline_key = None
        multiline_lines = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if multiline_key is not None:
            if line.startswith("      "):
                multiline_lines.append(line)
                continue
            flush_multiline()

        if line == "inputs:":
            in_inputs = True
            continue
        if in_inputs and line and not line.startswith(" "):
            flush_multiline()
            flush()
            break
        if not in_inputs:
            continue

        input_match = INPUT_NAME_RE.match(line)
        if input_match:
            flush_multiline()
            flush()
            current_name = input_match.group(1)
            continue

        property_match = PROPERTY_RE.match(line)
        if property_match and current_name is not None:
            key, value = property_match.groups()
            scalar = strip_yaml_scalar(value)
            if scalar in {"|", ">"}:
                multiline_key = key
                multiline_lines = []
            else:
                current[key] = scalar

    if in_inputs:
        flush_multiline()
        flush()
    return inputs


def _split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _strip_code(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1]
    return stripped


def parse_readme_inputs(path: Path) -> list[ReadmeInputRow]:
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index(README_INPUTS_HEADING)
    except ValueError as exc:
        raise ValueError(f"{path}: missing {README_INPUTS_HEADING}") from exc

    rows: list[ReadmeInputRow] = []
    in_table = False
    for line in lines[start + 1 :]:
        if line.startswith("## ") and line != README_INPUTS_HEADING:
            break
        if not line.startswith("|"):
            continue
        cells = _split_markdown_row(line)
        if cells[:4] == ["Input", "Required", "Default", "Description"]:
            in_table = True
            continue
        if in_table and cells[:4] == ["---", "---", "---", "---"]:
            continue
        if in_table and len(cells) >= 4:
            rows.append(
                ReadmeInputRow(
                    name=_strip_code(cells[0]),
                    required=cells[1],
                    default=_strip_code(cells[2]),
                    description=cells[3],
                )
            )
    return rows


def expected_readme_required(action_input: ActionInput) -> str:
    if action_input.required:
        return "Yes"
    if action_input.name in CONDITIONAL_REQUIRED:
        return "No*"
    return "No"


def expected_readme_default(action_input: ActionInput) -> str:
    if action_input.default is None:
        return "-"
    if action_input.default == "":
        return '""'
    return action_input.default


def validate_readme_inputs(action_inputs: list[ActionInput], readme_rows: list[ReadmeInputRow]) -> list[str]:
    errors: list[str] = []
    action_names = [item.name for item in action_inputs]
    readme_names = [row.name for row in readme_rows]
    if readme_names != action_names:
        missing = [name for name in action_names if name not in readme_names]
        extra = [name for name in readme_names if name not in action_names]
        if missing:
            errors.append(f"README inputs table is missing: {', '.join(missing)}")
        if extra:
            errors.append(f"README inputs table has unknown rows: {', '.join(extra)}")
        if not missing and not extra:
            errors.append("README inputs table order differs from action.yml")

    rows_by_name = {row.name: row for row in readme_rows}
    for action_input in action_inputs:
        row = rows_by_name.get(action_input.name)
        if row is None:
            continue
        expected_required = expected_readme_required(action_input)
        if row.required != expected_required:
            errors.append(
                f"README input `{action_input.name}` required={row.required!r}, expected {expected_required!r}"
            )
        expected_default = expected_readme_default(action_input)
        if row.default != expected_default:
            errors.append(
                f"README input `{action_input.name}` default={row.default!r}, expected {expected_default!r}"
            )
    return errors


def find_landfall_usage_inputs(path: Path) -> list[UsageInput]:
    usages: list[UsageInput] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    pending_landfall = False
    landfall_indent = 0
    collecting = False
    with_indent = 0

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if LANDFALL_USES_RE.match(line):
            pending_landfall = True
            landfall_indent = indent
            collecting = False
            continue

        with_match = WITH_RE.match(line)
        if pending_landfall and with_match:
            pending_landfall = False
            collecting = True
            with_indent = len(with_match.group(1))
            continue

        if collecting:
            if stripped and indent <= with_indent:
                collecting = False
            else:
                key_match = WITH_KEY_RE.match(line)
                if key_match:
                    usages.append(UsageInput(path=path, line_number=index, name=key_match.group(1)))

        if pending_landfall and stripped.startswith("- ") and indent <= landfall_indent:
            pending_landfall = False

    return usages


def validate_usage_inputs(action_inputs: list[ActionInput], paths: list[Path]) -> list[str]:
    errors: list[str] = []
    known = {item.name for item in action_inputs}
    deprecated = {item.name for item in action_inputs if item.deprecated}

    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        for usage in find_landfall_usage_inputs(path):
            if usage.name not in known:
                errors.append(f"{usage.path}:{usage.line_number}: unknown Landfall input `{usage.name}`")
            elif usage.name in deprecated:
                errors.append(f"{usage.path}:{usage.line_number}: deprecated Landfall input `{usage.name}`")
    return errors


def validate_deprecated_mentions(action_inputs: list[ActionInput], paths: list[Path]) -> list[str]:
    errors: list[str] = []
    deprecated = [item.name for item in action_inputs if item.deprecated]
    if not deprecated:
        return errors

    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        in_readme_inputs = False
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if path.name == "README.md" and line == README_INPUTS_HEADING:
                in_readme_inputs = True
            elif path.name == "README.md" and line == README_OUTPUTS_HEADING:
                in_readme_inputs = False

            for name in deprecated:
                pattern = re.compile(rf"(?<![A-Za-z0-9_-]){re.escape(name)}(?![A-Za-z0-9_-])")
                if not pattern.search(line):
                    continue
                if in_readme_inputs and line.startswith("|") and f"`{name}`" in line:
                    continue
                errors.append(
                    f"{path}:{line_number}: deprecated Landfall input `{name}` mentioned outside contract table"
                )
    return errors


def discover_default_scan_paths(repo_root: Path) -> list[Path]:
    paths: list[Path] = [repo_root / "README.md", repo_root / "CLAUDE.md", repo_root / "project.md"]
    for directory in (repo_root / "examples", repo_root / ".github" / "workflows"):
        if directory.exists():
            paths.extend(sorted(path for path in directory.glob("*.yml") if path.is_file()))
            paths.extend(sorted(path for path in directory.glob("*.yaml") if path.is_file()))
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate public Landfall action contract docs.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--action", type=Path, default=None)
    parser.add_argument("--readme", type=Path, default=None)
    parser.add_argument("--scan-path", type=Path, action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    action_path = args.action or repo_root / "action.yml"
    readme_path = args.readme or repo_root / "README.md"
    scan_paths = args.scan_path or discover_default_scan_paths(repo_root)

    errors: list[str] = []
    action_inputs = parse_action_inputs(action_path)
    if not action_inputs:
        errors.append(f"{action_path}: no action inputs found")
    else:
        try:
            readme_rows = parse_readme_inputs(readme_path)
            errors.extend(validate_readme_inputs(action_inputs, readme_rows))
        except ValueError as exc:
            errors.append(str(exc))
        errors.extend(validate_usage_inputs(action_inputs, scan_paths))
        errors.extend(validate_deprecated_mentions(action_inputs, scan_paths))

    if errors:
        for error in errors:
            print(f"contract error: {error}", file=sys.stderr)
        return 1

    print("Action contract ok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
