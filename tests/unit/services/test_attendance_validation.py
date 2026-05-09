"""Pure unit tests for the validation in the attendance service.

The validation runs before any DB call, so we can test it without a session.
DB-coupled behaviors (upsert idempotency, list queries) are integration tests.
"""

from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.services.attendance import (
    AttendanceValidationError,
    record_attendance,
)


async def test_record_attendance_rejects_invalid_status() -> None:
    db = cast(AsyncSession, AsyncMock())
    with pytest.raises(AttendanceValidationError, match="status"):
        await record_attendance(
            db,
            class_session_id=uuid4(),
            student_id=uuid4(),
            status="BANANAS",
            source="TEACHER",
        )


async def test_record_attendance_rejects_invalid_source() -> None:
    db = cast(AsyncSession, AsyncMock())
    with pytest.raises(AttendanceValidationError, match="source"):
        await record_attendance(
            db,
            class_session_id=uuid4(),
            student_id=uuid4(),
            status="PRESENT",
            source="JANITOR",
        )


async def test_record_attendance_validation_runs_before_db() -> None:
    """Validation errors must fire before any DB roundtrip; otherwise an agent
    sending a malformed status triggers a wasted transaction."""
    db = AsyncMock()
    with pytest.raises(AttendanceValidationError):
        await record_attendance(
            cast(AsyncSession, db),
            class_session_id=uuid4(),
            student_id=uuid4(),
            status="BAD",
            source="TEACHER",
        )
    db.execute.assert_not_called()
