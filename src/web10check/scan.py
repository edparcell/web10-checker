"""Static analysis of a single HTML document.

Produces a ParsedPage of raw findings (URLs unresolved, facts uninterpreted).
The checker resolves URLs and classifies first/third party; the rules turn
findings into faults.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup


@dataclass
class RawRef:
    """A resource reference found in the document."""

    url: str
    kind: str  # stylesheet | image | media | frame | preload | icon | object
    source: str  # short description of where it was found, e.g. "<img src>"


@dataclass
class ParsedPage:
    # JavaScript findings (JS-01)
    scripts: list[str] = field(default_factory=list)
    event_attrs: list[str] = field(default_factory=list)
    js_urls: list[str] = field(default_factory=list)
    script_preloads: list[str] = field(default_factory=list)
    script_srcs: list[str] = field(default_factory=list)  # also resources (TP-01, RQ-01)
    # Resource references (TP-01, WT-*, RQ-01, FR-01)
    refs: list[RawRef] = field(default_factory=list)
    iframes: list[str] = field(default_factory=list)
    # Autoplay (AV-01)
    autoplay: list[str] = field(default_factory=list)
    # Hygiene (HY-*)
    has_doctype: bool = False
    title: str | None = None
    html_lang: str | None = None
    meta_charset: str | None = None
    imgs_missing_alt: list[str] = field(default_factory=list)
    # Inline CSS to scan for url()/@import/@font-face
    inline_css: list[str] = field(default_factory=list)
    # Links for spidering
    anchors: list[str] = field(default_factory=list)


_SRCSET_URL = re.compile(r"(?:^|,)\s*(\S+)")


def _srcset_urls(value: str) -> list[str]:
    return [m for m in _SRCSET_URL.findall(value) if not m.startswith("data:")]


def _describe(tag) -> str:
    bits = [tag.name]
    for attr in ("id", "src", "href", "data"):
        v = tag.get(attr)
        if v:
            bits.append(f'{attr}="{str(v)[:80]}"')
            break
    return f"<{' '.join(bits)}>"


def parse_html(html: str) -> ParsedPage:
    page = ParsedPage()
    soup = BeautifulSoup(html, "html.parser")

    page.has_doctype = "<!doctype" in html[:2048].lower()

    html_tag = soup.find("html")
    if html_tag:
        lang = html_tag.get("lang")
        page.html_lang = lang.strip() if isinstance(lang, str) else None
    if soup.title and soup.title.string:
        page.title = soup.title.string.strip() or None

    for meta in soup.find_all("meta"):
        if meta.get("charset"):
            page.meta_charset = meta["charset"]
        elif (meta.get("http-equiv") or "").lower() == "content-type":
            content = meta.get("content") or ""
            if "charset=" in content.lower():
                page.meta_charset = content.split("=")[-1].strip()

    # Ignore <noscript> content: it is what a conforming visitor sees anyway.
    for noscript in soup.find_all("noscript"):
        noscript.decompose()

    for script in soup.find_all("script"):
        src = script.get("src")
        page.scripts.append(f'<script src="{src}">' if src else "inline <script>")
        if src and not src.startswith("data:"):
            page.script_srcs.append(src)

    for tag in soup.find_all(True):
        for attr, value in tag.attrs.items():
            if attr.lower().startswith("on") and len(attr) > 2:
                page.event_attrs.append(f'{attr} on {_describe(tag)}')
            if attr.lower() in ("href", "src", "action", "formaction"):
                if isinstance(value, str) and value.strip().lower().startswith("javascript:"):
                    page.js_urls.append(f'javascript: URL on {_describe(tag)}')
        if tag.name == "style" and tag.string:
            page.inline_css.append(tag.string)
        style_attr = tag.get("style")
        if style_attr:
            page.inline_css.append(str(style_attr))

    for link in soup.find_all("link"):
        rel = [r.lower() for r in (link.get("rel") or [])]
        href = link.get("href")
        if not href:
            continue
        as_attr = (link.get("as") or "").lower()
        if "modulepreload" in rel or ("preload" in rel and as_attr == "script"):
            page.script_preloads.append(f'<link rel="{" ".join(rel)}" href="{href[:80]}">')
            if not href.startswith("data:"):
                page.script_srcs.append(href)
        elif "stylesheet" in rel:
            page.refs.append(RawRef(href, "stylesheet", "<link rel=stylesheet>"))
        elif "icon" in rel or "apple-touch-icon" in rel:
            page.refs.append(RawRef(href, "icon", "<link rel=icon>"))
        elif "preload" in rel or "prefetch" in rel or "dns-prefetch" in rel or "preconnect" in rel:
            page.refs.append(RawRef(href, "preload", f'<link rel={" ".join(rel)}>'))

    for img in soup.find_all("img"):
        src = img.get("src")
        if src and not src.startswith("data:"):
            page.refs.append(RawRef(src, "image", "<img src>"))
        for u in _srcset_urls(img.get("srcset") or ""):
            page.refs.append(RawRef(u, "image", "<img srcset>"))
        if img.get("alt") is None:
            page.imgs_missing_alt.append(_describe(img))

    for source in soup.find_all("source"):
        src = source.get("src")
        if src and not src.startswith("data:"):
            page.refs.append(RawRef(src, "media", "<source src>"))
        for u in _srcset_urls(source.get("srcset") or ""):
            page.refs.append(RawRef(u, "media", "<source srcset>"))

    for tag_name in ("video", "audio"):
        for tag in soup.find_all(tag_name):
            src = tag.get("src")
            if src:
                page.refs.append(RawRef(src, "media", f"<{tag_name} src>"))
            poster = tag.get("poster")
            if poster:
                page.refs.append(RawRef(poster, "image", f"<{tag_name} poster>"))
            if tag.has_attr("autoplay"):
                page.autoplay.append(_describe(tag))

    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        if src and not src.startswith(("about:", "data:", "javascript:")):
            page.iframes.append(src)

    for obj in soup.find_all(("embed", "object")):
        target = obj.get("src") or obj.get("data")
        if target and not target.startswith("data:"):
            page.refs.append(RawRef(target, "object", f"<{obj.name}>"))

    for a in soup.find_all("a"):
        href = a.get("href")
        if href:
            page.anchors.append(href)

    return page
