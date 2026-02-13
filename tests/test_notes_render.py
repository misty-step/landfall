from __future__ import annotations


def test_markdown_to_html_fragment_renders_inline_markdown_in_h2(notes_render):
    markdown = "## Title with **bold** and `code` and [docs](https://example.com)\n"

    html = notes_render.markdown_to_html_fragment(markdown)

    assert "<h2>" in html
    assert "<strong>bold</strong>" in html
    assert "<code>code</code>" in html
    assert '<a href="https://example.com">docs</a>' in html


def test_safe_link_href_allows_http_and_https_only(notes_render):
    assert notes_render.safe_link_href("https://example.com") == "https://example.com"
    assert notes_render.safe_link_href("http://example.com") == "http://example.com"
    assert notes_render.safe_link_href("javascript:alert(1)") is None

