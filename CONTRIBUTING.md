# Contributing to Landfall

Thank you for your interest in contributing to Landfall! This document provides guidelines for setting up your development environment, running tests, and contributing code.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Linting](#linting)
- [Writing Tests](#writing-tests)
- [Commit Conventions](#commit-conventions)
- [Release Workflow](#release-workflow)

## Development Setup

### Prerequisites

- **Python 3.12+**
- **Node.js 22+** (for semantic-release)
- **Git**

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/misty-step/landfall.git
   cd landfall
   ```

2. **Install Python dependencies:**
   ```bash
   python -m pip install --upgrade pip
   python -m pip install requests pytest ruff check-jsonschema
   ```

3. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

4. **Verify your setup:**
   ```bash
   python -m ruff check scripts test
   python -m pytest -q test/
   ```

## Project Structure

```
landfall/
├── action.yml                  # GitHub Action definition
├── package.json                # Node.js dependencies (semantic-release)
├── configs/
│   └── .releaserc.json        # Default semantic-release configuration
├── scripts/
│   ├── synthesize.py          # LLM synthesis of user-facing notes
│   ├── update-release.py      # GitHub Release body updater
│   ├── report-synthesis-failure.py  # Failure reporting
│   ├── write-artifacts.py     # Artifact writer for notes
│   └── shared.py              # Shared utilities
├── templates/
│   └── synthesis-prompt.md    # LLM prompt template
├── test/
│   ├── conftest.py            # pytest fixtures and utilities
│   ├── test_synthesize.py
│   ├── test_update_release.py
│   ├── test_report_synthesis_failure.py
│   └── test_changelog_format.py
└── .github/workflows/
    ├── ci.yml                 # CI checks (lint + test)
    ├── release.yml            # Release workflow
    └── sync-v1-tag.yml        # Major tag synchronization
```

## Running Tests

We use **pytest** for testing. All tests are located in the `test/` directory.

### Run All Tests

```bash
python -m pytest -q test/
```

### Run Specific Test File

```bash
python -m pytest test/test_synthesize.py -v
```

### Run with Coverage (optional)

```bash
python -m pip install pytest-cov
python -m pytest --cov=scripts test/
```

### Test Fixtures

The `conftest.py` file provides fixtures for loading script modules dynamically:

- `synthesize` — Loaded `scripts/synthesize.py` module
- `update_release` — Loaded `scripts/update-release.py` module  
- `report_synthesis_failure` — Loaded `scripts/report-synthesis-failure.py` module

Example usage in tests:
```python
def test_something(synthesize):
    result = synthesize.some_function()
    assert result == expected
```

## Linting

We use **Ruff** for Python linting and code quality.

### Check All Code

```bash
python -m ruff check scripts test
```

### Check Specific File or Directory

```bash
python -m ruff check scripts/synthesize.py
python -m ruff check test/
```

### Auto-fix Issues

```bash
python -m ruff check scripts test --fix
```

### Validate GitHub Action Metadata

We also validate the `action.yml` file against the JSON schema:

```bash
python -m check_jsonschema \
  --schemafile https://json.schemastore.org/github-action.json \
  action.yml
```

## Writing Tests

When adding new features or fixing bugs, please include tests.

### Test Guidelines

1. **Test files** should be named `test_*.py` and placed in the `test/` directory
2. **Test functions** should be named `test_*` and use descriptive names
3. **Use fixtures** from `conftest.py` when testing script modules
4. **Mock external calls** — Use `unittest.mock` to mock HTTP requests and GitHub API calls

### Example Test Structure

```python
from unittest.mock import Mock, patch

def test_synthesize_with_valid_response(synthesize):
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "## What's New\n\nNew feature!"}}]
    }
    
    with patch("requests.post", return_value=mock_response):
        result = synthesize.call_llm(...)
        assert "New feature!" in result
```

## Commit Conventions

This repository uses **Conventional Commits** to automate versioning and changelog generation.

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description | Version Bump |
|------|-------------|--------------|
| `feat` | New feature | Minor |
| `fix` | Bug fix | Patch |
| `docs` | Documentation only changes | Patch |
| `style` | Code style (formatting, semicolons, etc.) | Patch |
| `refactor` | Code refactoring | Patch |
| `perf` | Performance improvements | Patch |
| `test` | Adding or correcting tests | Patch |
| `chore` | Build process, dependencies, etc. | Patch |

### Examples

```bash
# Feature
feat(synthesize): add fallback model chain support

# Bug fix
fix(update-release): handle empty release body

# Documentation
docs: update README with OpenAI provider example

# Refactoring
refactor(scripts): extract shared HTTP utilities
```

### Breaking Changes

For breaking changes, add `BREAKING CHANGE:` in the footer or use `!` after the type:

```
feat(api)!: change output format for release notes

BREAKING CHANGE: The `release-notes` output now returns markdown instead of HTML.
```

## Release Workflow

Landfall uses itself for releases via `semantic-release`. The process is fully automated.

### How Releases Work

1. **Commits are analyzed** — Conventional commits determine the version bump
2. **Version is calculated** — Based on commit types since last release
3. **CHANGELOG.md is updated** — New entry added automatically
4. **Git tag is created** — Format: `v{major}.{minor}.{patch}`
5. **GitHub Release is created** — With technical changelog
6. **User-facing notes are synthesized** — Via LLM and prepended to release
7. **Major tag is moved** — `v1` tag is force-pushed to the new release

### Triggering a Release

Simply merge your changes to `master`. The release workflow runs automatically:

```bash
# After PR is merged, the CI workflow validates
# Then the release workflow triggers automatically
```

### Release Configuration

The release configuration is in `configs/.releaserc.json`:

- `@semantic-release/commit-analyzer` — Determines version bump
- `@semantic-release/release-notes-generator` — Generates technical notes
- `@semantic-release/changelog` — Updates CHANGELOG.md
- `@semantic-release/git` — Commits version bump and changelog
- `@semantic-release/github` — Creates GitHub release

### Manual Release (for maintainers)

If needed, releases can be triggered manually:

1. Go to **Actions** → **Release** → **Run workflow**
2. Select the `master` branch
3. Click **Run workflow**

### Post-Release Verification

After a release, verify:

1. New version tag exists: `git tag | sort -V | tail -5`
2. CHANGELOG.md was updated correctly
3. GitHub Release has both technical notes and synthesized "What's New" section
4. `v1` tag points to the new release: `git show-ref v1`

## CI/CD

### Pull Request Checks

All PRs must pass:

- ✅ Python linting (Ruff)
- ✅ Unit tests (pytest)
- ✅ Action metadata validation

### Workflow Files

- `.github/workflows/ci.yml` — Runs on PRs and pushes to master
- `.github/workflows/release.yml` — Runs on pushes to master after CI passes
- `.github/workflows/cerberus.yml` — Security scanning
- `.github/workflows/sync-v1-tag.yml` — Keeps major version tag updated

## Getting Help

- **Questions?** Open a [Discussion](https://github.com/misty-step/landfall/discussions)
- **Bug reports?** Open an [Issue](https://github.com/misty-step/landfall/issues)
- **Security issues?** See [SECURITY.md](./SECURITY.md) (if available) or email maintainers privately

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
