from __future__ import annotations

import argparse
import datetime
import email.utils
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


def _parse_feed(path: Path) -> tuple[ET.Element, ET.Element, list[ET.Element]]:
    tree = ET.parse(path)
    root = tree.getroot()
    channel = root.find("channel")
    assert channel is not None
    items = channel.findall("item")
    return root, channel, items


def test_update_feed_creates_new_file(update_feed, tmp_path: Path):
    feed_path = tmp_path / "docs" / "releases.xml"
    published_at = datetime.datetime(2026, 2, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
    notes = "## Whats New\n\n- Added **bold** and `code` and [docs](https://example.com)\n"

    update_feed.update_feed_file(
        feed_path,
        repository="owner/repo",
        release_tag="v1.2.3",
        release_url="https://github.com/owner/repo/releases/tag/v1.2.3",
        notes_markdown=notes,
        published_at=published_at,
        max_entries=50,
    )

    assert feed_path.exists()
    _, channel, items = _parse_feed(feed_path)

    assert channel.findtext("title") == "repo Releases"
    assert channel.findtext("link") == "https://github.com/owner/repo/releases"

    assert len(items) == 1
    item = items[0]
    assert item.findtext("title") == "v1.2.3"
    assert item.findtext("link") == "https://github.com/owner/repo/releases/tag/v1.2.3"
    assert item.findtext("guid") == "https://github.com/owner/repo/releases/tag/v1.2.3"

    pub_date = email.utils.parsedate_to_datetime(item.findtext("pubDate") or "")
    assert pub_date == published_at

    description = item.findtext("description") or ""
    assert "<h2>Whats New</h2>" in description
    assert "<ul>" in description
    assert "<strong>bold</strong>" in description
    assert "<code>code</code>" in description
    assert '<a href="https://example.com">docs</a>' in description


def test_update_feed_rerun_updates_existing_item_no_duplicates(update_feed, tmp_path: Path):
    feed_path = tmp_path / "releases.xml"
    published_at = datetime.datetime(2026, 2, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
    release_url = "https://github.com/owner/repo/releases/tag/v1.2.3"

    update_feed.update_feed_file(
        feed_path,
        repository="owner/repo",
        release_tag="v1.2.3",
        release_url=release_url,
        notes_markdown="## Notes\n\n- First\n",
        published_at=published_at,
        max_entries=50,
    )

    update_feed.update_feed_file(
        feed_path,
        repository="owner/repo",
        release_tag="v1.2.3",
        release_url=release_url,
        notes_markdown="## Notes\n\n- Second\n",
        published_at=published_at,
        max_entries=50,
    )

    _, _, items = _parse_feed(feed_path)
    assert len(items) == 1
    description = items[0].findtext("description") or ""
    assert "Second" in description
    assert "First" not in description


def test_update_feed_trims_to_max_entries(update_feed, tmp_path: Path):
    feed_path = tmp_path / "releases.xml"
    release_base = "https://github.com/owner/repo/releases/tag/"

    update_feed.update_feed_file(
        feed_path,
        repository="owner/repo",
        release_tag="v1.0.0",
        release_url=f"{release_base}v1.0.0",
        notes_markdown="## Notes\n\n- 1\n",
        published_at=datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc),
        max_entries=2,
    )
    update_feed.update_feed_file(
        feed_path,
        repository="owner/repo",
        release_tag="v1.1.0",
        release_url=f"{release_base}v1.1.0",
        notes_markdown="## Notes\n\n- 2\n",
        published_at=datetime.datetime(2026, 2, 2, tzinfo=datetime.timezone.utc),
        max_entries=2,
    )
    update_feed.update_feed_file(
        feed_path,
        repository="owner/repo",
        release_tag="v1.2.0",
        release_url=f"{release_base}v1.2.0",
        notes_markdown="## Notes\n\n- 3\n",
        published_at=datetime.datetime(2026, 2, 3, tzinfo=datetime.timezone.utc),
        max_entries=2,
    )

    _, _, items = _parse_feed(feed_path)
    assert [item.findtext("title") for item in items] == ["v1.2.0", "v1.1.0"]


def test_cdata_escape_splits_illegal_sequence(update_feed):
    assert update_feed.cdata_escape("a]]>b") == "a]]]]><![CDATA[>b"


def test_validate_args_rejects_invalid_inputs(update_feed):
    with pytest.raises(ValueError, match="feed-file must be non-empty"):
        update_feed.validate_args(
            argparse.Namespace(
                feed_file=" ",
                max_entries=50,
                repository="owner/repo",
                release_tag="v1.2.3",
                release_url="https://example.com",
                notes_file="notes.md",
                workspace="",
                published_at="",
            )
        )

    with pytest.raises(ValueError, match="repository must be in owner/repo format"):
        update_feed.validate_args(
            argparse.Namespace(
                feed_file="feed.xml",
                max_entries=50,
                repository="invalid",
                release_tag="v1.2.3",
                release_url="https://example.com",
                notes_file="notes.md",
                workspace="",
                published_at="",
            )
        )

    with pytest.raises(ValueError, match="release-tag must be non-empty"):
        update_feed.validate_args(
            argparse.Namespace(
                feed_file="feed.xml",
                max_entries=50,
                repository="owner/repo",
                release_tag=" ",
                release_url="https://example.com",
                notes_file="notes.md",
                workspace="",
                published_at="",
            )
        )

    with pytest.raises(ValueError, match="release-url must be non-empty"):
        update_feed.validate_args(
            argparse.Namespace(
                feed_file="feed.xml",
                max_entries=50,
                repository="owner/repo",
                release_tag="v1.2.3",
                release_url=" ",
                notes_file="notes.md",
                workspace="",
                published_at="",
            )
        )

    with pytest.raises(ValueError, match="notes-file must be non-empty"):
        update_feed.validate_args(
            argparse.Namespace(
                feed_file="feed.xml",
                max_entries=50,
                repository="owner/repo",
                release_tag="v1.2.3",
                release_url="https://example.com",
                notes_file=" ",
                workspace="",
                published_at="",
            )
        )

    with pytest.raises(ValueError, match="max-entries must be > 0"):
        update_feed.validate_args(
            argparse.Namespace(
                feed_file="feed.xml",
                max_entries=0,
                repository="owner/repo",
                release_tag="v1.2.3",
                release_url="https://example.com",
                notes_file="notes.md",
                workspace="",
                published_at="",
            )
        )


def test_parse_iso8601_handles_z_suffix_offsets_and_naive(update_feed):
    assert update_feed.parse_iso8601("2026-02-10T12:00:00Z") == datetime.datetime(
        2026, 2, 10, 12, 0, 0, tzinfo=datetime.timezone.utc
    )
    assert update_feed.parse_iso8601("2026-02-10T14:00:00+02:00") == datetime.datetime(
        2026, 2, 10, 12, 0, 0, tzinfo=datetime.timezone.utc
    )
    assert update_feed.parse_iso8601("2026-02-10T12:00:00") == datetime.datetime(
        2026, 2, 10, 12, 0, 0, tzinfo=datetime.timezone.utc
    )

    with pytest.raises(ValueError):
        update_feed.parse_iso8601("not-a-date")


def test_parse_pubdate_returns_none_for_invalid(update_feed):
    assert update_feed.parse_pubdate("") is None
    assert update_feed.parse_pubdate("not-a-date") is None


def test_parse_pubdate_parses_rfc2822(update_feed):
    parsed = update_feed.parse_pubdate("Wed, 15 Jan 2025 10:30:00 GMT")
    assert parsed == datetime.datetime(2025, 1, 15, 10, 30, 0, tzinfo=datetime.timezone.utc)


def test_load_existing_feed_raises_for_missing_channel(update_feed, tmp_path: Path):
    feed = tmp_path / "feed.xml"
    feed.write_text('<?xml version="1.0"?><rss version="2.0"></rss>', encoding="utf-8")

    with pytest.raises(ValueError, match="missing channel"):
        update_feed.load_existing_feed(feed)


def test_load_existing_feed_raises_for_invalid_xml(update_feed, tmp_path: Path):
    feed = tmp_path / "feed.xml"
    feed.write_text("<rss", encoding="utf-8")

    with pytest.raises(ET.ParseError):
        update_feed.load_existing_feed(feed)


def test_resolve_feed_path_enforces_workspace_bounds(update_feed, tmp_path: Path):
    workspace = str(tmp_path)
    assert update_feed.resolve_feed_path("docs/releases.xml", workspace) == (tmp_path / "docs" / "releases.xml")
    assert update_feed.resolve_feed_path(str(tmp_path / "docs" / "releases.xml"), workspace) == (
        tmp_path / "docs" / "releases.xml"
    )

    with pytest.raises(ValueError, match="stay within workspace"):
        update_feed.resolve_feed_path("/abs/path.xml", workspace)

    with pytest.raises(ValueError, match="stay within workspace"):
        update_feed.resolve_feed_path("../escape.xml", workspace)


def test_main_returns_error_for_invalid_published_at(update_feed, tmp_path: Path, monkeypatch, capsys):
    notes = tmp_path / "notes.md"
    notes.write_text("## Notes\n- ok\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "update-feed.py",
            "--feed-file",
            "feed.xml",
            "--repository",
            "owner/repo",
            "--release-tag",
            "v1.2.3",
            "--release-url",
            "https://example.com",
            "--notes-file",
            str(notes),
            "--workspace",
            str(tmp_path),
            "--published-at",
            "not-a-date",
        ],
    )

    exit_code = update_feed.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "::error::" in captured.err


def test_main_returns_error_for_missing_notes_file(update_feed, tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "update-feed.py",
            "--feed-file",
            "feed.xml",
            "--repository",
            "owner/repo",
            "--release-tag",
            "v1.2.3",
            "--release-url",
            "https://example.com",
            "--notes-file",
            str(tmp_path / "missing.md"),
            "--workspace",
            str(tmp_path),
        ],
    )

    exit_code = update_feed.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "failed to read notes file" in captured.err


def test_main_returns_error_for_empty_notes_file(update_feed, tmp_path: Path, monkeypatch, capsys):
    notes = tmp_path / "notes.md"
    notes.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "update-feed.py",
            "--feed-file",
            "feed.xml",
            "--repository",
            "owner/repo",
            "--release-tag",
            "v1.2.3",
            "--release-url",
            "https://example.com",
            "--notes-file",
            str(notes),
            "--workspace",
            str(tmp_path),
        ],
    )

    exit_code = update_feed.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "notes file is empty" in captured.err


def test_main_returns_error_for_corrupt_existing_feed(update_feed, tmp_path: Path, monkeypatch, capsys):
    notes = tmp_path / "notes.md"
    notes.write_text("## Notes\n- ok\n", encoding="utf-8")

    feed = tmp_path / "feed.xml"
    feed.write_text("<rss", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "update-feed.py",
            "--feed-file",
            "feed.xml",
            "--repository",
            "owner/repo",
            "--release-tag",
            "v1.2.3",
            "--release-url",
            "https://example.com",
            "--notes-file",
            str(notes),
            "--workspace",
            str(tmp_path),
        ],
    )

    exit_code = update_feed.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "failed to update RSS feed" in captured.err


def test_main_returns_error_when_feed_file_escapes_workspace(update_feed, tmp_path: Path, monkeypatch, capsys):
    notes = tmp_path / "notes.md"
    notes.write_text("## Notes\n- ok\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "update-feed.py",
            "--feed-file",
            "../escape.xml",
            "--repository",
            "owner/repo",
            "--release-tag",
            "v1.2.3",
            "--release-url",
            "https://example.com",
            "--notes-file",
            str(notes),
            "--workspace",
            str(tmp_path),
        ],
    )

    exit_code = update_feed.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "stay within workspace" in captured.err
