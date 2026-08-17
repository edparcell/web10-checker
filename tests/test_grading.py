from web10check.grading import grade, is_pass, worst


def test_clean_sheet_is_a():
    assert grade(0, 0) == "A"


def test_minor_boundaries():
    assert grade(0, 1) == "B"
    assert grade(0, 4) == "B"
    assert grade(0, 5) == "C"
    assert grade(0, 9) == "C"
    assert grade(0, 10) == "D"  # minor overload fails, but is not an F


def test_major_boundaries():
    assert grade(1, 0) == "D"
    assert grade(1, 9) == "D"
    assert grade(1, 15) == "D"
    assert grade(2, 0) == "F"  # F means multiple major faults


def test_pass_fail():
    assert is_pass("A") and is_pass("B") and is_pass("C")
    assert not is_pass("D") and not is_pass("F")


def test_site_grade_is_worst_page():
    assert worst(["A", "C", "B"]) == "C"
    assert worst(["B", "F"]) == "F"
    assert worst([]) is None
