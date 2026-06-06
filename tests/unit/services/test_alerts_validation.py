"""Pure unit tests for the alerts service helpers + validation."""

from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from lizzie.services.alerts import (
    AlertValidationError,
    _rule_key_for_overdue_pass,
    _severity_for_overdue_pass,
    raise_alert,
)


def test_rule_key_for_restroom() -> None:
    assert _rule_key_for_overdue_pass("RESTROOM") == "hallpass.restroom.duration_exceeded"


def test_rule_key_for_nurse() -> None:
    assert _rule_key_for_overdue_pass("NURSE") == "hallpass.nurse.duration_exceeded"


def test_severity_restroom_is_high() -> None:
    """Restroom going long is the headline demo case -- on-duty admin must
    take it seriously, so it's high. Other destinations have legitimate
    longer durations and stay at medium until escalated."""
    assert _severity_for_overdue_pass("RESTROOM") == "high"


def test_severity_nurse_is_medium() -> None:
    assert _severity_for_overdue_pass("NURSE") == "medium"


def test_severity_counselor_is_medium() -> None:
    assert _severity_for_overdue_pass("COUNSELOR") == "medium"


async def test_raise_alert_rejects_invalid_severity() -> None:
    db = cast(AsyncSession, AsyncMock())
    with pytest.raises(AlertValidationError, match="severity"):
        await raise_alert(
            db,
            student_id=uuid4(),
            rule_key="anything",
            severity="urgent",  # not in enum
        )


async def test_raise_alert_validation_runs_before_db() -> None:
    db = AsyncMock()
    with pytest.raises(AlertValidationError):
        await raise_alert(
            cast(AsyncSession, db),
            student_id=uuid4(),
            rule_key="anything",
            severity="bad",
        )
    db.execute.assert_not_called()
