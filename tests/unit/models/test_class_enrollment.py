from datetime import date
from uuid import uuid4

from hpao.models import ClassEnrollment


def test_class_enrollment_construction() -> None:
    class_id = uuid4()
    student_id = uuid4()
    e = ClassEnrollment(
        class_id=class_id,
        student_id=student_id,
        enrolled_at=date(2025, 8, 15),
    )
    assert e.class_id == class_id
    assert e.student_id == student_id
    assert e.enrolled_at == date(2025, 8, 15)
