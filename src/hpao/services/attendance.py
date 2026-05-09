from __future__ import annotations

from datetime import date as date_type
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import (
    ATTENDANCE_SOURCES,
    ATTENDANCE_STATUSES,
    AttendanceRecord,
    ClassSession,
)


class AttendanceValidationError(ValueError):
    """Raised when status or source is not in the allowed enum."""


def _validate(status: str, source: str) -> None:
    if status not in ATTENDANCE_STATUSES:
        raise AttendanceValidationError(f"status {status!r} not in {ATTENDANCE_STATUSES}")
    if source not in ATTENDANCE_SOURCES:
        raise AttendanceValidationError(f"source {source!r} not in {ATTENDANCE_SOURCES}")


async def record_attendance(
    db: AsyncSession,
    *,
    class_session_id: UUID,
    student_id: UUID,
    status: str,
    source: str,
    recorded_by: UUID | None = None,
    notes: str | None = None,
) -> AttendanceRecord:
    """Idempotent upsert of an attendance row keyed on (class_session, student).

    Same (session, student) called twice -> the row is updated in place.
    Atomic at the DB layer via ON CONFLICT DO UPDATE; one round-trip.
    """
    _validate(status, source)

    insert_stmt = pg_insert(AttendanceRecord).values(
        class_session_id=class_session_id,
        student_id=student_id,
        status=status,
        source=source,
        recorded_by=recorded_by,
        notes=notes,
    )
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["class_session_id", "student_id"],
        set_={
            "status": insert_stmt.excluded.status,
            "source": insert_stmt.excluded.source,
            "recorded_by": insert_stmt.excluded.recorded_by,
            "notes": insert_stmt.excluded.notes,
            "updated_at": func.now(),
        },
    ).returning(AttendanceRecord)

    result = await db.execute(upsert_stmt)
    record = result.scalar_one()
    await db.flush()
    return record


async def list_attendance_for_session(
    db: AsyncSession, *, class_session_id: UUID
) -> list[AttendanceRecord]:
    stmt = select(AttendanceRecord).where(AttendanceRecord.class_session_id == class_session_id)
    return list((await db.execute(stmt)).scalars().all())


async def list_attendance_for_student(
    db: AsyncSession,
    *,
    student_id: UUID,
    since: date_type | None = None,
) -> list[AttendanceRecord]:
    stmt = (
        select(AttendanceRecord)
        .join(ClassSession, AttendanceRecord.class_session_id == ClassSession.id)
        .where(AttendanceRecord.student_id == student_id)
    )
    if since is not None:
        stmt = stmt.where(ClassSession.date >= since)
    stmt = stmt.order_by(ClassSession.date.desc())
    return list((await db.execute(stmt)).scalars().all())
