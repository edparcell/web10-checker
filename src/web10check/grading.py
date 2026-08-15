"""Grades, in the manner of the British driving test."""

from __future__ import annotations

GRADE_ORDER = "ABCDF"

VERDICTS = {
    "A": "A clean sheet. The examiner shakes your hand.",
    "B": "Pass.",
    "C": "Pass, but the examiner sighs quietly.",
    "D": "Fail. Rebook when ready.",
    "F": "Fail. Please surrender your keyboard at the desk.",
}


def grade(majors: int, minors: int) -> str:
    if majors >= 2 or minors >= 10:
        return "F"
    if majors == 1:
        return "D"
    if minors == 0:
        return "A"
    if minors <= 4:
        return "B"
    return "C"


def is_pass(letter: str) -> bool:
    return letter in ("A", "B", "C")


def worst(grades: list[str]) -> str | None:
    graded = [g for g in grades if g]
    if not graded:
        return None
    return max(graded, key=GRADE_ORDER.index)
