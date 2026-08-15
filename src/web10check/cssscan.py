"""Extract resource references and @font-face declarations from CSS text."""

from __future__ import annotations

import re

_URL = re.compile(r"url\(\s*['\"]?([^'\")\s]+)['\"]?\s*\)", re.IGNORECASE)
_IMPORT = re.compile(r"@import\s+(?:url\(\s*)?['\"]?([^'\")\s;]+)", re.IGNORECASE)
_FONT_FACE = re.compile(r"@font-face", re.IGNORECASE)
_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def scan_css(css: str) -> tuple[list[str], list[str], int]:
    """Return (resource URLs, @import URLs, count of @font-face blocks)."""
    css = _COMMENT.sub("", css)
    urls = [u for u in _URL.findall(css) if not u.startswith("data:")]
    imports = [u for u in _IMPORT.findall(css) if not u.startswith("data:")]
    # @import via url() is matched by both patterns; keep it only as an import.
    urls = [u for u in urls if u not in set(imports)]
    fonts = len(_FONT_FACE.findall(css))
    return urls, imports, fonts
