#!/usr/bin/env python3
"""Render Landfall release notes.

Small, dependency-free markdown renderers used for artifacts + feeds.
Intentionally minimal: headings, lists, links, code, bold.
"""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse


MARKDOWN_STRONG_RE = re.compile(r"\*\*(.+?)\*\*")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def markdown_inline_to_plaintext(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""

    def replace_link(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        url = match.group(2).strip()
        if not url:
            return label
        return f"{label} ({url})"

    stripped = MARKDOWN_LINK_RE.sub(replace_link, stripped)
    stripped = re.sub(r"`([^`]+)`", r"\1", stripped)
    stripped = MARKDOWN_STRONG_RE.sub(r"\1", stripped)
    stripped = stripped.replace("*", "").replace("_", "")
    stripped = re.sub(r"[ \t]+", " ", stripped)
    return stripped.strip()


def markdown_to_plaintext(markdown: str) -> str:
    lines = markdown.splitlines()
    rendered: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            rendered.append("")
            continue

        if line.startswith("## "):
            rendered.append(markdown_inline_to_plaintext(line[3:]))
            rendered.append("")
            continue

        if line.startswith("- "):
            rendered.append(f"- {markdown_inline_to_plaintext(line[2:])}")
            continue

        rendered.append(markdown_inline_to_plaintext(line))

    text = "\n".join(rendered).strip()
    return re.sub(r"\n{3,}", "\n\n", text) if text else ""


def safe_link_href(url: str) -> str | None:
    parsed = urlparse(url.strip())
    if parsed.scheme in ("http", "https"):
        return url.strip()
    return None


def markdown_inline_to_html(text: str) -> str:
    # Minimal inline renderer: links + code + strong. Everything else escaped.
    out: list[str] = []
    i = 0
    while i < len(text):
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1:
                strong = text[i + 2 : end]
                out.append(f"<strong>{html.escape(strong, quote=True)}</strong>")
                i = end + 2
                continue

        if text[i] == "`":
            end = text.find("`", i + 1)
            if end != -1:
                code = text[i + 1 : end]
                out.append(f"<code>{html.escape(code, quote=True)}</code>")
                i = end + 1
                continue

        if text[i] == "[":
            mid = text.find("](", i + 1)
            if mid != -1:
                end = text.find(")", mid + 2)
                if end != -1:
                    label = text[i + 1 : mid]
                    url = text[mid + 2 : end]
                    href = safe_link_href(url)
                    if href:
                        out.append(
                            f'<a href="{html.escape(href, quote=True)}">{html.escape(label, quote=True)}</a>'
                        )
                    else:
                        out.append(html.escape(label, quote=True))
                        if url.strip():
                            out.append(f" ({html.escape(url.strip(), quote=True)})")
                    i = end + 1
                    continue

        out.append(html.escape(text[i], quote=True))
        i += 1

    return "".join(out)


def markdown_to_html_fragment(markdown: str) -> str:
    lines = markdown.splitlines()
    rendered: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            rendered.append("</ul>")
            in_list = False

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            close_list()
            continue

        if stripped.startswith("## "):
            close_list()
            rendered.append(f"<h2>{markdown_inline_to_html(stripped[3:].strip())}</h2>")
            continue

        if stripped.startswith("- "):
            if not in_list:
                rendered.append("<ul>")
                in_list = True
            rendered.append(f"<li>{markdown_inline_to_html(stripped[2:].strip())}</li>")
            continue

        close_list()
        rendered.append(f"<p>{markdown_inline_to_html(stripped)}</p>")

    close_list()
    return "\n".join(rendered).strip()
