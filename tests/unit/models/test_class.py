from uuid import uuid4

from hpao.models import Class


def test_class_construction() -> None:
    school_id = uuid4()
    teacher_id = uuid4()
    c = Class(
        school_id=school_id,
        teacher_id=teacher_id,
        name="Algebra II",
        subject="math",
        period="3",
        room="B-204",
    )
    assert c.school_id == school_id
    assert c.teacher_id == teacher_id
    assert c.name == "Algebra II"
    assert c.period == "3"
    assert c.room == "B-204"


def test_class_subject_and_room_optional() -> None:
    c = Class(
        school_id=uuid4(),
        teacher_id=uuid4(),
        name="Homeroom",
        period="HR",
    )
    assert c.subject is None
    assert c.room is None


def test_class_repr_includes_name_and_period() -> None:
    c = Class(
        school_id=uuid4(),
        teacher_id=uuid4(),
        name="AP Biology",
        period="5",
    )
    rep = repr(c)
    assert "AP Biology" in rep
    assert "5" in rep
