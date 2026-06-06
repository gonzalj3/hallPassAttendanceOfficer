"""Service-level validation that runs before any DB roundtrip."""

from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from lizzie.services.hall_pass import HallPassValidationError, issue_pass


async def test_issue_pass_rejects_invalid_destination() -> None:
    db = cast(AsyncSession, AsyncMock())
    with pytest.raises(HallPassValidationError, match="destination"):
        await issue_pass(
            db,
            student_id=uuid4(),
            originating_class_session_id=uuid4(),
            destination="CAFETERIA",
            issued_by=uuid4(),
        )


async def test_issue_pass_validation_runs_before_db() -> None:
    db = AsyncMock()
    with pytest.raises(HallPassValidationError):
        await issue_pass(
            cast(AsyncSession, db),
            student_id=uuid4(),
            originating_class_session_id=uuid4(),
            destination="BAD",
            issued_by=uuid4(),
        )
    db.execute.assert_not_called()
