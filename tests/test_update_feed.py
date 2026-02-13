from __future__ import annotations

import datetime
import email.utils
import xml.etree.ElementTree as ET
from pathlib import Path


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

