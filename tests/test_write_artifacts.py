from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path
from types import ModuleType

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_script_module(module_name: str, relative_path: str) -> ModuleType:
    module_path = REPO_ROOT / relative_path
    scripts_dir = str(module_path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def write_artifacts():
    return load_script_module("landfall_write_artifacts", "scripts/write-artifacts.py")


def run_main(write_artifacts, monkeypatch, argv: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["write-artifacts.py", *argv])
    return write_artifacts.main()


def test_no_outputs_configured(write_artifacts, monkeypatch, capsys, tmp_path: Path):
    notes = "## What's New\n- Faster releases."
    notes_file = tmp_path / "notes.md"
    notes_file.write_text(notes, encoding="utf-8")

    exit_code = run_main(
        write_artifacts,
        monkeypatch,
        ["--notes-file", str(notes_file), "--version", "v1.2.0"],
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == notes


def test_output_file_basic(write_artifacts, monkeypatch, tmp_path: Path):
    notes = "## Highlights\n- Better docs."
    notes_file = tmp_path / "notes.md"
    output_file = tmp_path / "release.md"
    notes_file.write_text(notes, encoding="utf-8")

    exit_code = run_main(
        write_artifacts,
        monkeypatch,
        [
            "--notes-file",
            str(notes_file),
            "--version",
            "v1.2.0",
            "--output-file",
            str(output_file),
        ],
    )

    assert exit_code == 0
    assert output_file.read_text(encoding="utf-8") == notes


def test_output_file_version_interpolation(write_artifacts, monkeypatch, tmp_path: Path):
    notes = "## Highlights\n- Better docs."
    notes_file = tmp_path / "notes.md"
    notes_file.write_text(notes, encoding="utf-8")

    template = tmp_path / "docs" / "{version}.md"
    interpolated = tmp_path / "docs" / "v2.0.1.md"
    exit_code = run_main(
        write_artifacts,
        monkeypatch,
        [
            "--notes-file",
            str(notes_file),
            "--version",
            "v2.0.1",
            "--output-file",
            str(template),
        ],
    )

    assert exit_code == 0
    assert interpolated.exists()
    assert interpolated.read_text(encoding="utf-8") == notes


def test_output_file_creates_parent_dirs(write_artifacts, monkeypatch, tmp_path: Path):
    notes = "## Highlights\n- Better docs."
    notes_file = tmp_path / "notes.md"
    notes_file.write_text(notes, encoding="utf-8")

    output_file = tmp_path / "nested" / "releases" / "release.md"
    assert not output_file.parent.exists()

    exit_code = run_main(
        write_artifacts,
        monkeypatch,
        [
            "--notes-file",
            str(notes_file),
            "--version",
            "v2.0.1",
            "--output-file",
            str(output_file),
        ],
    )

    assert exit_code == 0
    assert output_file.parent.exists()
    assert output_file.read_text(encoding="utf-8") == notes


def test_output_json_creates_new_file(write_artifacts, monkeypatch, tmp_path: Path):
    notes = "## Highlights\n- Better docs."
    notes_file = tmp_path / "notes.md"
    output_json = tmp_path / "releases.json"
    notes_file.write_text(notes, encoding="utf-8")

    exit_code = run_main(
        write_artifacts,
        monkeypatch,
        [
            "--notes-file",
            str(notes_file),
            "--version",
            "1.2.0",
            "--output-json",
            str(output_json),
        ],
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload == [
        {
            "version": "1.2.0",
            "date": date.today().isoformat(),
            "notes": notes,
        }
    ]


def test_output_json_appends_to_existing(write_artifacts, monkeypatch, tmp_path: Path):
    notes = "## Highlights\n- Better docs."
    notes_file = tmp_path / "notes.md"
    output_json = tmp_path / "releases.json"
    notes_file.write_text(notes, encoding="utf-8")
    output_json.write_text(
        json.dumps([{"version": "1.1.0", "date": "2026-02-01", "notes": "old notes"}]),
        encoding="utf-8",
    )

    exit_code = run_main(
        write_artifacts,
        monkeypatch,
        [
            "--notes-file",
            str(notes_file),
            "--version",
            "1.2.0",
            "--output-json",
            str(output_json),
        ],
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert len(payload) == 2
    assert payload[1]["version"] == "1.2.0"
    assert payload[1]["date"] == date.today().isoformat()
    assert payload[1]["notes"] == notes


def test_output_json_invalid_root_type(write_artifacts, monkeypatch, tmp_path: Path):
    notes_file = tmp_path / "notes.md"
    output_json = tmp_path / "releases.json"
    notes_file.write_text("## Highlights\n- Better docs.", encoding="utf-8")
    output_json.write_text("{}", encoding="utf-8")

    exit_code = run_main(
        write_artifacts,
        monkeypatch,
        [
            "--notes-file",
            str(notes_file),
            "--version",
            "1.2.0",
            "--output-json",
            str(output_json),
        ],
    )

    assert exit_code == 1


def test_output_json_creates_parent_dirs(write_artifacts, monkeypatch, tmp_path: Path):
    notes_file = tmp_path / "notes.md"
    output_json = tmp_path / "nested" / "releases" / "releases.json"
    notes_file.write_text("## Highlights\n- Better docs.", encoding="utf-8")

    exit_code = run_main(
        write_artifacts,
        monkeypatch,
        [
            "--notes-file",
            str(notes_file),
            "--version",
            "1.2.0",
            "--output-json",
            str(output_json),
        ],
    )

    assert exit_code == 0
    assert output_json.parent.exists()
    assert output_json.exists()


def test_output_json_strips_v_prefix(write_artifacts, monkeypatch, tmp_path: Path):
    notes_file = tmp_path / "notes.md"
    output_json = tmp_path / "releases.json"
    notes_file.write_text("## Highlights\n- Better docs.", encoding="utf-8")

    exit_code = run_main(
        write_artifacts,
        monkeypatch,
        [
            "--notes-file",
            str(notes_file),
            "--version",
            "v1.2.0",
            "--output-json",
            str(output_json),
        ],
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload[0]["version"] == "1.2.0"


def test_both_outputs_configured(write_artifacts, monkeypatch, tmp_path: Path):
    notes = "## Highlights\n- Better docs."
    notes_file = tmp_path / "notes.md"
    output_file = tmp_path / "release.md"
    output_json = tmp_path / "releases.json"
    notes_file.write_text(notes, encoding="utf-8")

    exit_code = run_main(
        write_artifacts,
        monkeypatch,
        [
            "--notes-file",
            str(notes_file),
            "--version",
            "v1.2.0",
            "--output-file",
            str(output_file),
            "--output-json",
            str(output_json),
        ],
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert output_file.read_text(encoding="utf-8") == notes
    assert payload[0]["version"] == "1.2.0"
    assert payload[0]["notes"] == notes


def test_empty_notes_file(write_artifacts, monkeypatch, tmp_path: Path):
    empty_notes_file = tmp_path / "empty.md"
    empty_notes_file.write_text("", encoding="utf-8")

    exit_code = run_main(
        write_artifacts,
        monkeypatch,
        ["--notes-file", str(empty_notes_file), "--version", "v1.2.0"],
    )

    assert exit_code == 1


def test_missing_notes_file(write_artifacts, monkeypatch, tmp_path: Path):
    exit_code = run_main(
        write_artifacts,
        monkeypatch,
        ["--notes-file", str(tmp_path / "missing.md"), "--version", "v1.2.0"],
    )

    assert exit_code == 1


def test_validate_args_empty_version(write_artifacts):
    args = argparse.Namespace(
        notes_file="notes.md",
        version="   ",
        output_file="",
        output_json="",
        log_level="INFO",
    )

    with pytest.raises(ValueError, match="version must be non-empty"):
        write_artifacts.validate_args(args)
