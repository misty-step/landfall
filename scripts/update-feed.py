#!/usr/bin/env python3
"""Update an RSS 2.0 feed file with synthesized Landfall release notes."""

from __future__ import annotations

import argparse
import datetime
import email.utils
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from notes_render import markdown_to_html_fragment


@dataclass(frozen=True)
class FeedChannel:
    title: str
    link: str
    description: str


@dataclass(frozen=True)
class FeedItem:
    title: str
    link: str
    guid: str
    pub_date: datetime.datetime
    description_html: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update an RSS feed file with release notes.")
    parser.add_argument("--feed-file", required=True, help="RSS feed file path to create/update.")
    parser.add_argument("--max-entries", type=int, default=50, help="Maximum number of feed items to retain.")
    parser.add_argument("--repository", required=True, help="GitHub repository in owner/repo format.")
    parser.add_argument("--release-tag", required=True, help="Release tag (e.g., v1.2.3).")
    parser.add_argument("--release-url", required=True, help="Release URL for the item link/guid.")
    parser.add_argument("--notes-file", required=True, help="Path to synthesized notes markdown file.")
    parser.add_argument(
        "--published-at",
        default="",
        help="Optional ISO8601 timestamp for pubDate (tests/determinism). Defaults to now UTC.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.feed_file or not args.feed_file.strip():
        raise ValueError("feed-file must be non-empty")
    if not args.repository or "/" not in args.repository:
        raise ValueError("repository must be in owner/repo format")
    if not args.release_tag or not args.release_tag.strip():
        raise ValueError("release-tag must be non-empty")
    if not args.release_url or not args.release_url.strip():
        raise ValueError("release-url must be non-empty")
    if not args.notes_file or not args.notes_file.strip():
        raise ValueError("notes-file must be non-empty")
    if args.max_entries <= 0:
        raise ValueError("max-entries must be > 0")


def parse_iso8601(timestamp: str) -> datetime.datetime:
    value = timestamp.strip()
    if not value:
        raise ValueError("timestamp must be non-empty")
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    dt = datetime.datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def format_rfc2822(dt: datetime.datetime) -> str:
    aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=datetime.timezone.utc)
    return email.utils.format_datetime(aware.astimezone(datetime.timezone.utc), usegmt=True)


def parse_pubdate(value: str) -> datetime.datetime | None:
    text = value.strip()
    if not text:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def default_channel(repository: str) -> FeedChannel:
    owner, repo = repository.split("/", 1)
    return FeedChannel(
        title=f"{repo} Releases",
        link=f"https://github.com/{owner}/{repo}/releases",
        description=f"Release notes for {owner}/{repo}.",
    )


def load_existing_feed(path: Path) -> tuple[FeedChannel, list[FeedItem]]:
    tree = ET.parse(path)
    root = tree.getroot()
    channel_el = root.find("channel")
    if channel_el is None:
        raise ValueError("invalid RSS feed: missing channel element")

    title = (channel_el.findtext("title") or "").strip()
    link = (channel_el.findtext("link") or "").strip()
    description = (channel_el.findtext("description") or "").strip()
    channel = FeedChannel(
        title=title or "Releases",
        link=link or "",
        description=description or "",
    )

    items: list[FeedItem] = []
    for item_el in channel_el.findall("item"):
        item_title = (item_el.findtext("title") or "").strip()
        item_link = (item_el.findtext("link") or "").strip()
        guid = (item_el.findtext("guid") or "").strip() or item_link or item_title
        pub_date = parse_pubdate(item_el.findtext("pubDate") or "") or datetime.datetime.min.replace(
            tzinfo=datetime.timezone.utc
        )
        description_html = (item_el.findtext("description") or "").strip()
        items.append(
            FeedItem(
                title=item_title,
                link=item_link,
                guid=guid,
                pub_date=pub_date,
                description_html=description_html,
            )
        )

    return channel, items


def ensure_parent_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def cdata_escape(text: str) -> str:
    # Prevent illegal "]]>" in CDATA by splitting sections.
    return text.replace("]]>", "]]]]><![CDATA[>")


def xml_text(text: str) -> str:
    return escape(text, entities={})


def build_rss_xml(channel: FeedChannel, items: list[FeedItem], *, last_build_date: datetime.datetime) -> str:
    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "  <channel>",
        f"    <title>{xml_text(channel.title)}</title>",
        f"    <link>{xml_text(channel.link)}</link>",
        f"    <description>{xml_text(channel.description)}</description>",
        f"    <lastBuildDate>{xml_text(format_rfc2822(last_build_date))}</lastBuildDate>",
    ]

    for item in items:
        lines.extend(
            [
                "    <item>",
                f"      <title>{xml_text(item.title)}</title>",
                f"      <link>{xml_text(item.link)}</link>",
                f"      <guid>{xml_text(item.guid)}</guid>",
                f"      <pubDate>{xml_text(format_rfc2822(item.pub_date))}</pubDate>",
                f"      <description><![CDATA[{cdata_escape(item.description_html)}]]></description>",
                "    </item>",
            ]
        )

    lines.extend(["  </channel>", "</rss>", ""])
    return "\n".join(lines)


def item_key(item: FeedItem) -> str:
    return item.guid or item.link or item.title


def merge_item(items: list[FeedItem], new_item: FeedItem, *, max_entries: int) -> list[FeedItem]:
    by_key: dict[str, FeedItem] = {}
    for existing in items:
        key = item_key(existing)
        if key and key not in by_key:
            by_key[key] = existing

    by_key[item_key(new_item)] = new_item

    merged = list(by_key.values())
    merged.sort(key=lambda item: item.pub_date, reverse=True)
    return merged[:max_entries]


def update_feed_file(
    path: Path,
    *,
    repository: str,
    release_tag: str,
    release_url: str,
    notes_markdown: str,
    published_at: datetime.datetime,
    max_entries: int,
) -> None:
    channel = default_channel(repository)
    items: list[FeedItem] = []

    if path.exists():
        existing_channel, items = load_existing_feed(path)
        channel = FeedChannel(
            title=existing_channel.title or channel.title,
            link=existing_channel.link or channel.link,
            description=existing_channel.description or channel.description,
        )

    description_html = markdown_to_html_fragment(notes_markdown)
    new_item = FeedItem(
        title=release_tag.strip(),
        link=release_url.strip(),
        guid=release_url.strip(),
        pub_date=published_at,
        description_html=description_html,
    )

    merged = merge_item(items, new_item, max_entries=max_entries)

    ensure_parent_directory(path)
    rss_xml = build_rss_xml(channel, merged, last_build_date=published_at)
    path.write_text(rss_xml, encoding="utf-8")


def main() -> int:
    args = parse_args()

    try:
        validate_args(args)
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    published_at = datetime.datetime.now(tz=datetime.timezone.utc)
    if args.published_at.strip():
        try:
            published_at = parse_iso8601(args.published_at)
        except ValueError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 1

    notes_path = Path(args.notes_file)
    try:
        notes = notes_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        print(f"::error::failed to read notes file: {exc}", file=sys.stderr)
        return 1

    if not notes:
        print("::error::notes file is empty", file=sys.stderr)
        return 1

    feed_path = Path(args.feed_file)
    try:
        update_feed_file(
            feed_path,
            repository=args.repository,
            release_tag=args.release_tag,
            release_url=args.release_url,
            notes_markdown=notes,
            published_at=published_at,
            max_entries=args.max_entries,
        )
    except (OSError, ValueError, ET.ParseError) as exc:
        print(f"::error::failed to update RSS feed: {exc}", file=sys.stderr)
        return 1

    print(f"::notice::updated RSS feed: {feed_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

