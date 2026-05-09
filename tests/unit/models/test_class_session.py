from datetime import date, time
from uuid import uuid4

from hpao.models import ClassSession


def test_class_session_construction() -> None:
    class_id = uuid4()
    cs = ClassSession(
        class_id=class_id,
        date=date(2025, 9, 4),
        scheduled_start=time(9, 0),
        scheduled_end=time(9, 50),
    )
    assert cs.class_id == class_id
    assert cs.date == date(2025, 9, 4)
    assert cs.scheduled_start == time(9, 0)
    assert cs.scheduled_end == time(9, 50)


def test_class_session_repr_includes_date() -> None:
    cs = ClassSession(
        class_id=uuid4(),
        date=date(2025, 9, 4),
        scheduled_start=time(9, 0),
        scheduled_end=time(9, 50),
    )
    assert "2025-09-04" in repr(cs)
