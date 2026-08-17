"""Fetch backends: live HTTP and local directory (pre-deploy checking).

Both expose the same interface:
- fetch_page(url) -> FetchResult
- classify(base_url, ref) -> (disposition, absolute_url) where disposition is
  "internal", "external", or "skip"
- resource_size(url) -> (size_in_bytes | None, set_cookie_seen)
- page_link(base_url, href) -> absolute url of a same-site page to spider, or None

The checker never fetches external resources; their presence alone is the
fault (TP-01), and fetching them would make the checker the surveillance.
"""

from __future__ import annotations

import posixpath
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit

import httpx

from .origins import same_site

DEFAULT_UA = "web10-checker/0.3 (Certified Web 1.0 conformance test)"
_RESOURCE_BYTE_CAP = 4 * 1024 * 1024
_SKIP_SCHEMES = ("mailto:", "tel:", "data:", "about:", "javascript:", "ftp:", "gopher:", "gemini:")

# Requests are shaped like a browser's (HTTP/2, full header set) so that
# edges serve what they serve real visitors. Cloudflare, for example, only
# injects its analytics beacon into responses for traffic it believes is a
# browser; a bare HTTP/1.1 fetch receives an artificially clean page and
# would grade it A while actual visitors get a tracking script.
_BROWSER_HEADERS = {
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}
_FETCH_ERRORS = (httpx.HTTPError, httpx.InvalidURL, httpx.CookieConflict, ValueError)


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int | None
    content: bytes
    text: str
    content_type: str
    set_cookie: bool
    error: str | None = None


class HttpFetcher:
    def __init__(self, user_agent: str = DEFAULT_UA, timeout: float = 20.0):
        headers = dict(_BROWSER_HEADERS)
        headers["User-Agent"] = user_agent
        self.client = httpx.Client(http2=True, headers=headers,
                                   timeout=timeout, follow_redirects=True)

    def fetch_page(self, url: str) -> FetchResult:
        try:
            resp = self.client.get(url)
        except _FETCH_ERRORS as exc:
            return FetchResult(url, url, None, b"", "", "", False,
                               error=str(exc) or type(exc).__name__)
        error = None if resp.status_code < 400 else f"HTTP {resp.status_code}"
        return FetchResult(
            url=url,
            final_url=str(resp.url),
            status=resp.status_code,
            content=resp.content,
            text=resp.text,
            content_type=resp.headers.get("Content-Type", ""),
            set_cookie="set-cookie" in resp.headers,
            error=error,
        )

    def classify(self, base_url: str, ref: str) -> tuple[str, str]:
        ref = ref.strip()
        if not ref or ref.startswith("#") or ref.lower().startswith(_SKIP_SCHEMES):
            return "skip", ref
        absolute = urldefrag(urljoin(base_url, ref)).url
        parts = urlsplit(absolute)
        if parts.scheme not in ("http", "https"):
            return "skip", absolute
        base_host = urlsplit(base_url).hostname or ""
        host = parts.hostname or ""
        if same_site(base_host, host):
            return "internal", absolute
        return "external", absolute

    def resource_size(self, url: str) -> tuple[int | None, bool]:
        set_cookie = False
        try:
            head = self.client.head(url)
            set_cookie = "set-cookie" in head.headers
            length = head.headers.get("Content-Length")
            if length is not None and head.status_code < 400:
                return int(length), set_cookie
            total = 0
            with self.client.stream("GET", url) as resp:
                set_cookie = set_cookie or "set-cookie" in resp.headers
                for chunk in resp.iter_bytes(65536):
                    total += len(chunk)
                    if total >= _RESOURCE_BYTE_CAP:
                        break
            return total, set_cookie
        except _FETCH_ERRORS:
            return None, set_cookie

    def page_link(self, base_url: str, href: str) -> str | None:
        disposition, absolute = self.classify(base_url, href)
        if disposition != "internal":
            return None
        return absolute


class LocalFetcher:
    """Checks a static site in a local directory before it is deployed.

    Pages are identified by resolved absolute file paths. Any absolute
    http(s) reference is treated as third-party (see SPEC.md).
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def resolve_target(self, target: str | Path) -> str:
        path = Path(target).resolve()  # relative targets are relative to cwd
        if path.is_dir():
            path = path / "index.html"
        return path.as_posix()

    def fetch_page(self, url: str) -> FetchResult:
        path = Path(url)
        try:
            content = path.read_bytes()
        except OSError as exc:
            return FetchResult(url, url, None, b"", "", "", False, error=str(exc))
        return FetchResult(
            url=url,
            final_url=url,
            status=200,
            content=content,
            text=content.decode("utf-8", errors="replace"),
            content_type="text/html; charset=utf-8",
            set_cookie=False,
        )

    def _resolve_path(self, base_url: str, ref: str) -> str:
        if ref.startswith("/"):
            joined = (self.root.as_posix() + "/" + ref.lstrip("/"))
        else:
            joined = posixpath.join(posixpath.dirname(base_url), ref)
        return posixpath.normpath(joined)

    def classify(self, base_url: str, ref: str) -> tuple[str, str]:
        ref = ref.strip()
        if not ref or ref.startswith("#"):
            return "skip", ref
        lower = ref.lower()
        if lower.startswith(_SKIP_SCHEMES):
            return "skip", ref
        if lower.startswith(("http://", "https://", "//")):
            return "external", ref
        ref = ref.split("#")[0].split("?")[0]
        if not ref:
            return "skip", ref
        resolved = self._resolve_path(base_url, ref)
        if not resolved.startswith(self.root.as_posix()):
            return "external", resolved
        return "internal", resolved

    def resource_size(self, url: str) -> tuple[int | None, bool]:
        path = Path(url)
        if path.is_file():
            return path.stat().st_size, False
        return None, False

    def page_link(self, base_url: str, href: str) -> str | None:
        disposition, absolute = self.classify(base_url, href)
        if disposition != "internal":
            return None
        path = Path(absolute)
        if path.is_dir():
            path = path / "index.html"
        if path.suffix.lower() not in (".html", ".htm"):
            return None
        return path.as_posix()
