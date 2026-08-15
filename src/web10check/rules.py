"""The rules of the Web 1.0 Specification (2026 Edition).

Each rule inspects a fully-assembled PageData and returns its occurrences.
Major faults count once per rule per page; minor faults count per occurrence,
capped at MINOR_CAP per rule per page.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MINOR_CAP = 3
WEIGHT_MAJOR = 2 * 1024 * 1024
WEIGHT_MINOR = 512 * 1024
REQUEST_LIMIT = 20


@dataclass
class PageData:
    url: str
    # JS-01
    scripts: list[str] = field(default_factory=list)
    event_attrs: list[str] = field(default_factory=list)
    js_urls: list[str] = field(default_factory=list)
    script_preloads: list[str] = field(default_factory=list)
    # TP-01
    external_refs: list[str] = field(default_factory=list)
    # CK-01
    cookies: list[str] = field(default_factory=list)
    # WT-01 / WT-02 / RQ-01
    total_bytes: int = 0
    request_count: int = 0
    # AV-01
    autoplay: list[str] = field(default_factory=list)
    # HY-*
    has_doctype: bool = True
    title: str | None = None
    html_lang: str | None = None
    charset: str | None = None
    imgs_missing_alt: list[str] = field(default_factory=list)
    # FT-01
    font_faces: list[str] = field(default_factory=list)
    # FR-01
    internal_iframes: list[str] = field(default_factory=list)


def _fmt_bytes(n: int) -> str:
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / (1024 * 1024):.2f} MB"


RULES = [
    # (id, name, severity, check)
    ("JS-01", "JavaScript", "major",
     lambda d: d.scripts + d.event_attrs + d.js_urls + d.script_preloads),
    ("TP-01", "Third-party requests", "major",
     lambda d: d.external_refs),
    ("CK-01", "Cookies", "major",
     lambda d: d.cookies),
    ("WT-01", "Gross obesity (over 2 MB)", "major",
     lambda d: [f"total first-party transfer {_fmt_bytes(d.total_bytes)}"]
     if d.total_bytes > WEIGHT_MAJOR else []),
    ("AV-01", "Autoplaying media", "major",
     lambda d: d.autoplay),
    ("HY-01", "Missing doctype", "minor",
     lambda d: [] if d.has_doctype else ["no <!DOCTYPE html>"]),
    ("HY-02", "Missing title", "minor",
     lambda d: [] if d.title else ["no <title>, or an empty one"]),
    ("HY-03", "Missing language", "minor",
     lambda d: [] if d.html_lang else ["no lang attribute on <html>"]),
    ("HY-04", "Missing charset", "minor",
     lambda d: [] if d.charset else ["no character-encoding declaration"]),
    ("HY-05", "Missing alt text", "minor",
     lambda d: d.imgs_missing_alt),
    ("FT-01", "Web fonts", "minor",
     lambda d: d.font_faces),
    ("WT-02", "Overweight (over 512 KB)", "minor",
     lambda d: [f"total first-party transfer {_fmt_bytes(d.total_bytes)}"]
     if WEIGHT_MINOR < d.total_bytes <= WEIGHT_MAJOR else []),
    ("RQ-01", "Chatty (over 20 requests)", "minor",
     lambda d: [f"{d.request_count} resource requests"]
     if d.request_count > REQUEST_LIMIT else []),
    ("FR-01", "First-party frame", "minor",
     lambda d: d.internal_iframes),
]


def evaluate(data: PageData):
    """Return (rule_results, majors, minors)."""
    from .models import RuleResult

    results = []
    majors = 0
    minors = 0
    for rule_id, name, severity, check in RULES:
        occurrences = list(check(data))
        if severity == "major":
            counted = 1 if occurrences else 0
            majors += counted
        else:
            counted = min(len(occurrences), MINOR_CAP)
            minors += counted
        results.append(RuleResult(rule_id, name, severity, occurrences, counted))
    return results, majors, minors
