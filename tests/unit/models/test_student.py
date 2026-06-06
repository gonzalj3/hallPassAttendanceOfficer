from datetime import date
from uuid import uuid4

from lizzie.models import GRADE_LEVELS, Student


def test_student_construction() -> None:
    school_id = uuid4()
    s = Student(
        school_id=school_id,
        student_number="S001",
        grade_level="10",
        first_name="Alice",
        last_name="Garcia",
        enrolled_at=date(2025, 8, 15),
    )
    assert s.school_id == school_id
    assert s.first_name == "Alice"
    assert s.last_name == "Garcia"
    assert s.grade_level == "10"
    assert s.student_number == "S001"


def test_kindergarten_grade_level_uses_K() -> None:
    s = Student(
        school_id=uuid4(),
        student_number="S002",
        grade_level="K",
        first_name="Bob",
        last_name="Lee",
        enrolled_at=date(2025, 8, 15),
    )
    assert s.grade_level == "K"


def test_grade_levels_constant_covers_K_through_12() -> None:
    assert GRADE_LEVELS[0] == "K"
    assert GRADE_LEVELS[-1] == "12"
    assert len(GRADE_LEVELS) == 13


def test_student_repr_contains_name_and_grade() -> None:
    s = Student(
        school_id=uuid4(),
        student_number="S001",
        grade_level="10",
        first_name="Alice",
        last_name="Garcia",
        enrolled_at=date(2025, 8, 15),
    )
    rep = repr(s)
    assert "Garcia" in rep
    assert "Alice" in rep
    assert "10" in rep
