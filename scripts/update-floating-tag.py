#!/usr/bin/env python3
"""Parse a semver release tag and output the floating major version tag."""

from __future__ import annotations

import argparse
import re
import sys


def parse_major_tag(release_tag: str) -> str | None:
    """Extract 'vN' from stable semver tags; return None for pre-release tags."""
    match = re.match(r"^v?(\d+)\.\d+\.\d+$", release_tag)
    if match:
        return f"v{match.group(1)}"

    # Pre-release tags should not move floating major tags.
    if re.match(r"^v?\d+\.\d+\.\d+-", release_tag):
        return None

    raise ValueError(f"invalid semver tag: {release_tag}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Output floating major tag for a release.")
    parser.add_argument("--release-tag", required=True)
    args = parser.parse_args(argv)

    try:
        major_tag = parse_major_tag(args.release_tag)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    if major_tag is None:
        return

    print(major_tag)


if __name__ == "__main__":
    main()
