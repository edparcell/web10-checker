"""Result dataclasses shared across the checker."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RuleResult:
    rule_id: str
    name: str
    severity: str  # "major" | "minor"
    occurrences: list[str] = field(default_factory=list)
    counted: int = 0  # faults counted toward the grade (minors are capped)

    @property
    def passed(self) -> bool:
        return not self.occurrences

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "severity": self.severity,
            "passed": self.passed,
            "counted": self.counted,
            "occurrences": self.occurrences,
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
