"""Pydantic request/response shapes for the browser-facing REST surface.

Field names use camelCase to match the frontend TypeScript types.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DestinationLiteral = Literal[
    "RESTROOM", "OFFICE", "NURSE", "HALLWAY", "CLASSROOM", "COUNSELOR", "OTHER"
]
HallPassStatusLiteral = Literal["ACTIVE", "RETURNED", "OVERDUE", "FLAGGED"]
ClassPeriodTypeLiteral = Literal["suggested", "advisory", "lunch", "regular"]
AlertStatusLiteral = Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"]
SeverityLiteral = Literal["low", "medium", "high", "critical"]


class _CamelBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class StudentOut(_CamelBase):
    id: UUID
    name: str = Field(description="Display name: first + last")
    student_number: str = Field(serialization_alias="studentNumber")
    grade_level: int = Field(
        serialization_alias="gradeLevel",
        description="Numeric grade (Kindergarten -> 0).",
    )


class ClassPeriodOut(_CamelBase):
    id: UUID = Field(description="ClassSession id — what /api/sessions/{id}/students keys off")
    class_id: UUID = Field(serialization_alias="classId")
    school_id: UUID = Field(serialization_alias="schoolId")
    name: str
    subject: str
    period: str
    start_time: str = Field(serialization_alias="startTime")
    end_time: str = Field(serialization_alias="endTime")
    room: str
    teacher_id: UUID = Field(serialization_alias="teacherId")
    student_count: int = Field(serialization_alias="studentCount")
    type: ClassPeriodTypeLiteral


class HallPassOut(_CamelBase):
    id: UUID
    student_id: UUID = Field(serialization_alias="studentId")
    student_name: str = Field(serialization_alias="studentName")
    destination: DestinationLiteral
    checked_out_at: datetime = Field(serialization_alias="checkedOutAt")
    expected_return_at: datetime = Field(serialization_alias="expectedReturnAt")
    checked_in_at: datetime | None = Field(default=None, serialization_alias="checkedInAt")
    status: HallPassStatusLiteral


class RosterOut(_CamelBase):
    session: ClassPeriodOut
    students: list[StudentOut]
    active_passes: list[HallPassOut] = Field(serialization_alias="activePasses")


class IssueHallPassIn(_CamelBase):
    student_id: UUID = Field(validation_alias="studentId")
    session_id: UUID = Field(
        validation_alias="sessionId", description="ClassSession id from GET /api/sessions"
    )
    destination: DestinationLiteral
    reason: str | None = None
    duration_minutes: int | None = Field(
        default=None,
        validation_alias="durationMinutes",
        description="Override default duration. Demo path uses 1 to fast-trip the alert.",
        ge=1,
    )


StatsRangeLiteral = Literal["today", "week", "month"]


class StatsOut(_CamelBase):
    """Dashboard headline KPIs. Snapshot metrics (`outNow`, `overdueNow`)
    always reflect right-now; window metrics honor the `range` query
    parameter."""

    range: StatsRangeLiteral
    out_now: int = Field(serialization_alias="outNow")
    overdue_now: int = Field(serialization_alias="overdueNow")
    total_issued: int = Field(serialization_alias="totalIssued")
    returned_in_window: int = Field(serialization_alias="returnedInWindow")
    avg_duration_seconds: int = Field(serialization_alias="avgDurationSeconds")


class AlertSummaryOut(_CamelBase):
    id: UUID
    student_id: UUID = Field(serialization_alias="studentId")
    student_name: str = Field(serialization_alias="studentName")
    rule_key: str = Field(serialization_alias="ruleKey")
    severity: SeverityLiteral
    status: AlertStatusLiteral
    context: dict[str, Any]
    created_at: datetime = Field(serialization_alias="createdAt")
