from uuid import uuid4

from hpao.models import (
    ATTENDANCE_SOURCES,
    ATTENDANCE_STATUSES,
    AttendanceRecord,
)


def test_attendance_record_construction() -> None:
    session_id = uuid4()
    student_id = uuid4()
    teacher_id = uuid4()
    r = AttendanceRecord(
        class_session_id=session_id,
        student_id=student_id,
        status="PRESENT",
        source="TEACHER",
        recorded_by=teacher_id,
        notes="on time",
    )
    assert r.class_session_id == session_id
    assert r.student_id == student_id
    assert r.status == "PRESENT"
    assert r.source == "TEACHER"
    assert r.recorded_by == teacher_id
    assert r.notes == "on time"


def test_attendance_recorded_by_and_notes_optional() -> None:
    r = AttendanceRecord(
        class_session_id=uuid4(),
        student_id=uuid4(),
        status="ABSENT",
        source="AGENT",
    )
    assert r.recorded_by is None
    assert r.notes is None


def test_status_constants_cover_demo_set() -> None:
    assert "PRESENT" in ATTENDANCE_STATUSES
    assert "ABSENT" in ATTENDANCE_STATUSES
    assert "TARDY" in ATTENDANCE_STATUSES
    assert "EXCUSED" in ATTENDANCE_STATUSES
    assert "UNEXCUSED" in ATTENDANCE_STATUSES
    assert len(ATTENDANCE_STATUSES) == 5


def test_source_constants_cover_demo_set() -> None:
    assert ATTENDANCE_SOURCES == ("TEACHER", "AGENT", "IMPORT")


def test_attendance_repr_includes_status() -> None:
    r = AttendanceRecord(
        class_session_id=uuid4(),
        student_id=uuid4(),
        status="TARDY",
        source="TEACHER",
    )
    assert "TARDY" in repr(r)
