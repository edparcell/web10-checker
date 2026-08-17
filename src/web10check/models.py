"""Result dataclasses shared across the checker."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Finding:
    """A single fault occurrence. Severity belongs to the finding, not the
    rule: one rule may grade minor at one threshold and major at another."""

    severity: str  # "major" | "minor"
    detail: str

    def to_dict(self) -> dict:
        return {"severity": self.severity, "detail": self.detail}


@dataclass
class RuleResult:
    rule_id: str
    name: str
    findings: list[Finding] = field(default_factory=list)
    majors: int = 0  # counted majors (at most 1 per rule per page)
    minors: int = 0  # counted minors (capped per rule per page)

    @property
    def passed(self) -> bool:
        return not self.findings

    @property
    def occurrences(self) -> list[str]:
        return [f.detail for f in self.findings]

    @property
    def counted(self) -> int:
        return self.majors + self.minors

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "passed": self.passed,
            "majors": self.majors,
            "minors": self.minors,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class PageResult:
    url: str
    ok: bool
    error: str | None = None
    status: int | None = None
    grade: str | None = None
    majors: int = 0
    minors: int = 0
    weight_bytes: int = 0
    request_count: int = 0
    rule_results: list[RuleResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "ok": self.ok,
            "error": self.error,
            "status": self.status,
            "grade": self.grade,
            "majors": self.majors,
            "minors": self.minors,
            "weight_bytes": self.weight_bytes,
            "request_count": self.request_count,
            "rules": [r.to_dict() for r in self.rule_results],
        }


@dataclass
class SiteResult:
    targets: list[str]
    pages: list[PageResult] = field(default_factory=list)
    grade: str | None = None
    spec_edition: str = "2026"
    checked_at: str | None = None  # ISO timestamp, set by the CLI

    def to_dict(self) -> dict:
        return {
            "spec_edition": self.spec_edition,
            "checked_at": self.checked_at,
            "targets": self.targets,
            "grade": self.grade,
            "pages": [p.to_dict() for p in self.pages],
        }
