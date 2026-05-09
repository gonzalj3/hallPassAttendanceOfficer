"""Pydantic request/response shapes for the browser-facing REST surface.

Field names use camelCase to match the existing frontend TypeScript types
(`frontend/src/types/index.ts`) byte-for-byte, so the React code can drop
straight from `mockData.ts` onto a real `fetch()` without renaming props.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Mirrors hall_pass.HALL_PASS_DESTINATIONS so the API rejects unknown
# strings before the DB CHECK constraint does.
DestinationLiteral = Literal[
    "RESTROOM", "OFFICE", "NURSE", "HALLWAY", "CLASSROOM", "COUNSELOR", "OTHER"
]
HallPassStatusLiteral = Literal["ACTIVE", "RETURNED", "OVERDUE", "FLAGGED"]
ClassPeriodTypeLiteral = Literal["suggested", "advisory", "lunch", "regular"]


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
    """Combined roster + active passes for the RosterPage."""

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
