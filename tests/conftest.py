from __future__ import annotations

import pytest

from web10check.checker import check_page
from web10check.fetcher import FetchResult, HttpFetcher


class StubFetcher(HttpFetcher):
    """HttpFetcher with the network replaced by a dict. classify() and
    page_link() keep the real same-site logic."""

    def __init__(self, pages: dict, sizes: dict | None = None,
                 cookie_urls: set | None = None, page_cookies: set | None = None,
                 html_content_type: str = "text/html; charset=utf-8"):
        super().__init__()
        self.pages = pages
        self.sizes = sizes or {}
        self.cookie_urls = cookie_urls or set()
        self.page_cookies = page_cookies or set()
        self.html_content_type = html_content_type

    def fetch_page(self, url: str) -> FetchResult:
        if url not in self.pages:
            return FetchResult(url, url, 404, b"", "", "", False, error="HTTP 404")
        body = self.pages[url]
        content = body.encode("utf-8") if isinstance(body, str) else body
        content_type = "text/css" if url.endswith(".css") else self.html_content_type
        return FetchResult(url, url, 200, content,
                           content.decode("utf-8", errors="replace"),
                           content_type, url in self.page_cookies)

    def resource_size(self, url: str):
        return self.sizes.get(url, 1000), url in self.cookie_urls


CLEAN_PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Test</title></head>
<body><h1>Hello</h1><p>A perfectly ordinary page.</p></body></html>"""


@pytest.fixture
def check_html():
    """Check a single page of HTML (plus optional extra first-party files)."""

    def _check(html: str, url: str = "https://example.com/", **stub_kwargs):
        pages = {url: html}
        pages.update(stub_kwargs.pop("extra_pages", {}))
        return check_page(StubFetcher(pages, **stub_kwargs), url)

    return _check


def rule(page_result, rule_id: str):
    return next(r for r in page_result.rule_results if r.rule_id == rule_id)
