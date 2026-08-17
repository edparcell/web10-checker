"""The rules of the Web 1.0 Specification (2026 Edition).

Each rule inspects a fully-assembled PageData and returns findings, and
each finding carries its own severity: one rule may grade minor at one
threshold and major at another. Major faults are counted once per rule per
page; minor faults are counted per occurrence, capped at MINOR_CAP per
rule per page.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Finding

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
    # WT-01 / RQ-01
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


def _majors(details) -> list[Finding]:
    return [Finding("major", d) for d in details]


def _minors(details) -> list[Finding]:
    return [Finding("minor", d) for d in details]


def _weight(d: PageData) -> list[Finding]:
    detail = f"total first-party transfer {_fmt_bytes(d.total_bytes)}"
    if d.total_bytes > WEIGHT_MAJOR:
        return [Finding("major", f"{detail} (over 2 MB)")]
    if d.total_bytes > WEIGHT_MINOR:
        return [Finding("minor", f"{detail} (over 512 KB)")]
    return []


RULES = [
    # (id, name, check) - check returns findings, each with a severity
    ("JS-01", "JavaScript",
     lambda d: _majors(d.scripts + d.event_attrs + d.js_urls + d.script_preloads)),
    ("TP-01", "Third-party requests",
     lambda d: _majors(d.external_refs)),
    ("CK-01", "Cookies",
     lambda d: _majors(d.cookies)),
    ("WT-01", "Excessive transfer", _weight),
    ("AV-01", "Autoplaying media",
     lambda d: _majors(d.autoplay)),
    ("HY-01", "Missing doctype",
     lambda d: [] if d.has_doctype else _minors(["no <!DOCTYPE html>"])),
    ("HY-02", "Missing title",
     lambda d: [] if d.title else _minors(["no <title>, or an empty one"])),
    ("HY-03", "Missing language",
     lambda d: [] if d.html_lang else _minors(["no lang attribute on <html>"])),
    ("HY-04", "Missing charset",
     lambda d: [] if d.charset else _minors(["no character-encoding declaration"])),
    ("HY-05", "Missing alt text",
     lambda d: _minors(d.imgs_missing_alt)),
    ("FT-01", "Web fonts",
     lambda d: _minors(d.font_faces)),
    ("RQ-01", "Excessive requests",
     lambda d: _minors([f"{d.request_count} resource requests"])
     if d.request_count > REQUEST_LIMIT else []),
    ("FR-01", "First-party frame",
     lambda d: _minors(d.internal_iframes)),
]


def evaluate(data: PageData):
    """Return (rule_results, majors, minors)."""
    from .models import RuleResult

    results = []
    majors = 0
    minors = 0
    for rule_id, name, check in RULES:
        findings = list(check(data))
        rule_majors = 1 if any(f.severity == "major" for f in findings) else 0
        rule_minors = min(
            sum(1 for f in findings if f.severity == "minor"), MINOR_CAP)
        majors += rule_majors
        minors += rule_minors
        results.append(RuleResult(rule_id, name, findings,
                                  rule_majors, rule_minors))
    return results, majors, minors
