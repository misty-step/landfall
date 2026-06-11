from __future__ import annotations

from pathlib import Path


def test_validate_readme_inputs_catches_default_drift(check_action_contract):
    action_inputs = [
        check_action_contract.ActionInput(
            name="synthesis-failure-issue",
            required=False,
            default="false",
            description="Whether to create an issue.",
        )
    ]
    readme_rows = [
        check_action_contract.ReadmeInputRow(
            name="synthesis-failure-issue",
            required="No",
            default="true",
            description="Whether to create an issue.",
        )
    ]

    errors = check_action_contract.validate_readme_inputs(action_inputs, readme_rows)

    assert errors == ["README input `synthesis-failure-issue` default='true', expected 'false'"]


def test_validate_readme_inputs_catches_missing_input(check_action_contract):
    action_inputs = [
        check_action_contract.ActionInput("synthesis", False, "true", "Whether to synthesize."),
        check_action_contract.ActionInput("healthcheck", False, "false", "Validate LLM key."),
    ]
    readme_rows = [
        check_action_contract.ReadmeInputRow("synthesis", "No", "true", "Whether to synthesize."),
    ]

    errors = check_action_contract.validate_readme_inputs(action_inputs, readme_rows)

    assert errors == ["README inputs table is missing: healthcheck"]


def test_find_landfall_usage_inputs_reads_active_and_commented_keys(check_action_contract, tmp_path: Path):
    workflow = tmp_path / "workflow.yml"
    workflow.write_text(
        """
jobs:
  release:
    steps:
      - uses: misty-step/landfall@v1
        with:
          github-token: ${{ secrets.GH_RELEASE_TOKEN }}
          # synthesis-strict: "true"
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
""",
        encoding="utf-8",
    )

    usages = check_action_contract.find_landfall_usage_inputs(workflow)

    assert [(usage.line_number, usage.name) for usage in usages] == [
        (7, "github-token"),
        (8, "synthesis-strict"),
    ]


def test_find_landfall_usage_inputs_allows_step_keys_before_with(check_action_contract, tmp_path: Path):
    workflow = tmp_path / "workflow.yml"
    workflow.write_text(
        """
steps:
  - uses: misty-step/landfall@v1
    if: github.ref == 'refs/heads/master'
    env:
      SAMPLE: value
    with:
      github-token: ${{ secrets.GH_RELEASE_TOKEN }}
""",
        encoding="utf-8",
    )

    usages = check_action_contract.find_landfall_usage_inputs(workflow)

    assert [(usage.line_number, usage.name) for usage in usages] == [(8, "github-token")]


def test_validate_usage_inputs_rejects_unknown_and_deprecated_inputs(check_action_contract, tmp_path: Path):
    workflow = tmp_path / "workflow.yml"
    workflow.write_text(
        """
steps:
  - uses: ./
    with:
      github-token: ${{ secrets.GH_RELEASE_TOKEN }}
      old-input: true
      synthesis-strict: "true"
""",
        encoding="utf-8",
    )
    action_inputs = [
        check_action_contract.ActionInput("github-token", True, None, "GitHub token."),
        check_action_contract.ActionInput("synthesis-strict", False, "false", "Deprecated alias."),
    ]

    errors = check_action_contract.validate_usage_inputs(action_inputs, [workflow])

    assert errors == [
        f"{workflow}:6: unknown Landfall input `old-input`",
        f"{workflow}:7: deprecated Landfall input `synthesis-strict`",
    ]


def test_parse_action_inputs_reads_multiline_deprecated_description(check_action_contract, tmp_path: Path):
    action = tmp_path / "action.yml"
    action.write_text(
        """
name: Example
inputs:
  synthesis-strict:
    description: |
      Deprecated alias for synthesis-required.
      Keep for compatibility.
    default: "false"
    required: false
outputs: {}
""",
        encoding="utf-8",
    )

    inputs = check_action_contract.parse_action_inputs(action)

    assert inputs == [
        check_action_contract.ActionInput(
            name="synthesis-strict",
            required=False,
            default="false",
            description="Deprecated alias for synthesis-required. Keep for compatibility.",
        )
    ]
    assert inputs[0].deprecated


def test_validate_deprecated_mentions_allows_readme_table_only(check_action_contract, tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text(
        """
# Project

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `synthesis-strict` | No | `false` | Deprecated alias. |

## Outputs

Do not use synthesis-strict in examples.
""",
        encoding="utf-8",
    )
    project = tmp_path / "project.md"
    project.write_text("Old setup mentioned synthesis-strict here.\n", encoding="utf-8")
    action_inputs = [
        check_action_contract.ActionInput("synthesis-strict", False, "false", "Deprecated alias."),
    ]

    errors = check_action_contract.validate_deprecated_mentions(action_inputs, [readme, project])

    assert errors == [
        f"{readme}:12: deprecated Landfall input `synthesis-strict` mentioned outside contract table",
        f"{project}:1: deprecated Landfall input `synthesis-strict` mentioned outside contract table",
    ]


def test_validate_deprecated_mentions_uses_token_boundaries(check_action_contract, tmp_path: Path):
    project = tmp_path / "project.md"
    project.write_text("This pre-synthesis-strict-mode phrase is not the input name.\n", encoding="utf-8")
    action_inputs = [
        check_action_contract.ActionInput("synthesis-strict", False, "false", "Deprecated alias."),
    ]

    errors = check_action_contract.validate_deprecated_mentions(action_inputs, [project])

    assert errors == []


def test_parse_readme_inputs_extracts_contract_table(check_action_contract, tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text(
        """
# Project

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `mode` | No | `full` | Pipeline mode. |

## Outputs
""",
        encoding="utf-8",
    )

    rows = check_action_contract.parse_readme_inputs(readme)

    assert rows == [check_action_contract.ReadmeInputRow("mode", "No", "full", "Pipeline mode.")]
