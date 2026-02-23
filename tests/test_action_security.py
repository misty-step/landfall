from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ACTION_PATH = REPO_ROOT / "action.yml"


def _run_block_violations(forbidden_token: str) -> list[tuple[int, str]]:
    lines = ACTION_PATH.read_text(encoding="utf-8").splitlines()
    violations: list[tuple[int, str]] = []
    in_run_block = False
    run_indent = 0

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))

        if in_run_block:
            if stripped and indent <= run_indent:
                in_run_block = False
            elif forbidden_token in line:
                violations.append((line_number, stripped))

        if stripped.startswith("run: |"):
            in_run_block = True
            run_indent = indent

    return violations


def test_action_run_blocks_do_not_inline_inputs_expressions() -> None:
    violations = _run_block_violations("${{ inputs.")
    assert not violations, f"inline inputs expressions in run blocks: {violations}"


def test_action_run_blocks_do_not_inline_step_output_expressions() -> None:
    violations = _run_block_violations("${{ steps.")
    assert not violations, f"inline steps expressions in run blocks: {violations}"
