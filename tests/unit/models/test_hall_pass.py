from datetime import UTC, datetime, timedelta
from uuid import uuid4

from lizzie.models import HALL_PASS_DESTINATIONS, HALL_PASS_STATUSES, HallPass


def test_hall_pass_construction() -> None:
    student_id = uuid4()
    cs_id = uuid4()
    issuer_id = uuid4()
    now = datetime.now(UTC)
    p = HallPass(
        student_id=student_id,
        originating_class_session_id=cs_id,
        destination="RESTROOM",
        checked_out_at=now,
        expected_return_at=now + timedelta(minutes=15),
        status="ACTIVE",
        issued_by=issuer_id,
    )
    assert p.student_id == student_id
    assert p.destination == "RESTROOM"
    assert p.status == "ACTIVE"
    assert p.checked_in_at is None


def test_hall_pass_statuses_enum() -> None:
    assert HALL_PASS_STATUSES == ("ACTIVE", "RETURNED", "OVERDUE", "FLAGGED")


def test_hall_pass_destinations_enum() -> None:
    # HALLWAY + CLASSROOM added in migration 0009 to match the frontend's
    # destination vocabulary.
    assert set(HALL_PASS_DESTINATIONS) == {
        "RESTROOM",
        "NURSE",
        "COUNSELOR",
        "OFFICE",
        "OTHER",
        "HALLWAY",
        "CLASSROOM",
    }


def test_hall_pass_repr_includes_status_and_destination() -> None:
    now = datetime.now(UTC)
    p = HallPass(
        student_id=uuid4(),
        originating_class_session_id=uuid4(),
        destination="NURSE",
        checked_out_at=now,
        expected_return_at=now + timedelta(minutes=30),
        status="ACTIVE",
        issued_by=uuid4(),
    )
    rep = repr(p)
    assert "ACTIVE" in rep
    assert "NURSE" in rep
