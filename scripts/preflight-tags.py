#!/usr/bin/env python3
"""Preflight check for orphaned git tag history.

Detects when version tags exist in the repo but none are reachable from
HEAD. This causes semantic-release to treat the next push as a "first
release" (v1.0.0), which collides with existing tags and spams
CHANGELOG.md with duplicate entries.

See: https://github.com/misty-step/landfall/issues/86
"""

from __future__ import annotations

import re
import subprocess
import sys

VERSION_TAG_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")


def _semver_key(tag: str) -> tuple[int, int, int]:
    """Extract (major, minor, patch) for sorting. Non-matches sort last."""
    m = VERSION_TAG_RE.match(tag)
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def get_all_tags() -> list[str]:
    result = subprocess.run(
        ["git", "tag"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [t for t in result.stdout.strip().splitlines() if t]


def get_reachable_tags() -> list[str]:
    result = subprocess.run(
        ["git", "tag", "--merged", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [t for t in result.stdout.strip().splitlines() if t]


def get_current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def filter_version_tags(tags: list[str]) -> list[str]:
    return [t for t in tags if VERSION_TAG_RE.match(t)]


def diagnose_orphaned_tags(
    *,
    all_tags: list[str],
    reachable_tags: list[str],
) -> dict[str, object] | None:
    """Return diagnostic dict if orphaned version tags detected, else None."""
    version_tags = filter_version_tags(all_tags)
    if not version_tags:
        return None

    reachable_version = filter_version_tags(reachable_tags)
    if reachable_version:
        return None

    sorted_tags = sorted(version_tags, key=_semver_key)
    return {
        "count": len(version_tags),
        "earliest": sorted_tags[0],
        "latest": sorted_tags[-1],
    }


def main() -> int:
    all_tags = get_all_tags()
    reachable = get_reachable_tags()

    diag = diagnose_orphaned_tags(all_tags=all_tags, reachable_tags=reachable)
    if diag is None:
        return 0

    branch = get_current_branch()
    latest = diag["latest"]
    count = diag["count"]
    earliest = diag["earliest"]

    print(
        f"::error::Orphaned tag history detected on branch '{branch}'.",
        file=sys.stderr,
    )
    print(
        f"::error::Found {count} version tag(s) ({earliest}..{latest}) "
        f"but none are reachable from HEAD.",
        file=sys.stderr,
    )
    print(
        "::error::semantic-release will miscalculate the next version "
        "(likely 1.0.0), collide with existing tags, and spam CHANGELOG.md.",
        file=sys.stderr,
    )
    print(
        f"::error::Fix: connect tag history to '{branch}':",
        file=sys.stderr,
    )
    print(
        f'::error::  git merge -s ours --allow-unrelated-histories {latest} '
        f'-m "chore(git): connect legacy release tags to {branch}"',
        file=sys.stderr,
    )
    print(f"::error::  git push origin {branch}", file=sys.stderr)

    return 1


if __name__ == "__main__":
    sys.exit(main())
