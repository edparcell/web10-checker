"""Orchestration: fetch a page, assemble PageData, evaluate rules, spider."""

from __future__ import annotations

from collections import deque
from urllib.parse import urlsplit

from . import SPEC_EDITION
from .cssscan import scan_css
from .fetcher import FetchResult, HttpFetcher, LocalFetcher
from .grading import grade, worst
from .models import PageResult, SiteResult
from .rules import PageData, evaluate
from .scan import parse_html

_CSS_IMPORT_DEPTH = 3


def _charset_from_content_type(content_type: str) -> str | None:
    for part in content_type.split(";"):
        part = part.strip().lower()
        if part.startswith("charset="):
            return part.split("=", 1)[1]
    return None


def check_page(fetcher, url: str) -> PageResult:
    fr: FetchResult = fetcher.fetch_page(url)
    if fr.error and not fr.content:
        return PageResult(url=url, ok=False, error=fr.error, status=fr.status)

    base = fr.final_url
    parsed = parse_html(fr.text)

    external: list[str] = []   # occurrence descriptions for TP-01
    cookies: list[str] = []
    font_faces: list[str] = []
    internal_iframes: list[str] = []
    seen_requests: set[str] = set()
    total_bytes = len(fr.content)
    if fr.set_cookie:
        cookies.append(f"Set-Cookie on {url}")

    internal_css: list[tuple[str, str]] = []  # (css_url, disposition source)
    internal_resources: list[str] = []

    def note_request(absolute: str) -> bool:
        if absolute in seen_requests:
            return False
        seen_requests.add(absolute)
        return True

    def classify_ref(ref_url: str, source: str, kind: str, base_url: str) -> None:
        disposition, absolute = fetcher.classify(base_url, ref_url)
        if disposition == "skip" or not note_request(absolute):
            return
        if disposition == "external":
            external.append(f"{absolute} (via {source})")
        elif kind == "stylesheet":
            internal_css.append((absolute, source))
        else:
            internal_resources.append(absolute)

    for ref in parsed.refs:
        classify_ref(ref.url, ref.source, ref.kind, base)

    for iframe_src in parsed.iframes:
        disposition, absolute = fetcher.classify(base, iframe_src)
        if disposition == "skip" or not note_request(absolute):
            continue
        if disposition == "external":
            external.append(f"{absolute} (via <iframe>)")
        else:
            internal_iframes.append(absolute)

    # Inline CSS (style tags and attributes)
    for css_text in parsed.inline_css:
        urls, imports, fonts = scan_css(css_text)
        font_faces.extend(["@font-face in inline CSS"] * fonts)
        for u in urls:
            classify_ref(u, "inline CSS url()", "cssref", base)
        for u in imports:
            classify_ref(u, "inline CSS @import", "stylesheet", base)

    # First-party stylesheets: fetch, weigh, and scan (imports followed to a depth)
    css_queue = deque((css_url, 0) for css_url, _ in internal_css)
    while css_queue:
        css_url, depth = css_queue.popleft()
        css_fr = fetcher.fetch_page(css_url)
        if css_fr.error and not css_fr.content:
            continue
        total_bytes += len(css_fr.content)
        if css_fr.set_cookie:
            cookies.append(f"Set-Cookie on {css_url}")
        urls, imports, fonts = scan_css(css_fr.text)
        font_faces.extend([f"@font-face in {css_url}"] * fonts)
        for u in urls:
            classify_ref(u, f"url() in {css_url}", "cssref", css_url)
        for u in imports:
            disposition, absolute = fetcher.classify(css_url, u)
            if disposition == "skip" or not note_request(absolute):
                continue
            if disposition == "external":
                external.append(f"{absolute} (via @import in {css_url})")
            elif depth < _CSS_IMPORT_DEPTH:
                css_queue.append((absolute, depth + 1))

    # Weigh remaining first-party resources (never fetches third parties)
    for res_url in internal_resources:
        size, set_cookie = fetcher.resource_size(res_url)
        if size:
            total_bytes += size
        if set_cookie:
            cookies.append(f"Set-Cookie on {res_url}")

    data = PageData(
        url=url,
        scripts=parsed.scripts,
        event_attrs=parsed.event_attrs,
        js_urls=parsed.js_urls,
        script_preloads=parsed.script_preloads,
        external_refs=external,
        cookies=cookies,
        total_bytes=total_bytes,
        request_count=1 + len(seen_requests),
        autoplay=parsed.autoplay,
        has_doctype=parsed.has_doctype,
        title=parsed.title,
        html_lang=parsed.html_lang,
        charset=parsed.meta_charset or _charset_from_content_type(fr.content_type),
        imgs_missing_alt=parsed.imgs_missing_alt,
        font_faces=font_faces,
        internal_iframes=internal_iframes,
    )
    rule_results, majors, minors = evaluate(data)
    result = PageResult(
        url=url,
        ok=True,
        status=fr.status,
        grade=grade(majors, minors),
        majors=majors,
        minors=minors,
        weight_bytes=total_bytes,
        request_count=data.request_count,
        rule_results=rule_results,
    )
    result._anchors = parsed.anchors  # for the spider; not serialized
    return result


def check_targets(fetcher, targets: list[str], spider: bool = False,
                  max_pages: int = 25) -> SiteResult:
    site = SiteResult(targets=list(targets), spec_edition=SPEC_EDITION)
    queue = deque(targets)
    visited: set[str] = set()
    while queue and len(site.pages) < max_pages:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        page = check_page(fetcher, url)
        site.pages.append(page)
        if spider and page.ok:
            for href in getattr(page, "_anchors", []):
                link = fetcher.page_link(url, href)
                if link and link not in visited:
                    queue.append(link)
    site.grade = worst([p.grade for p in site.pages if p.ok])
    return site


def make_fetcher(target: str, user_agent: str | None = None, timeout: float = 20.0):
    """Pick a backend from the first target: URL -> HTTP, path -> local."""
    if urlsplit(target).scheme in ("http", "https"):
        kwargs = {"timeout": timeout}
        if user_agent:
            kwargs["user_agent"] = user_agent
        return HttpFetcher(**kwargs)
    from pathlib import Path

    path = Path(target)
    root = path if path.is_dir() else path.parent
    return LocalFetcher(root)
