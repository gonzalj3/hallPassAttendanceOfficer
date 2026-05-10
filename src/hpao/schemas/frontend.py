"""Pydantic request/response shapes for the browser-facing REST surface.

Field names use camelCase to match the existing frontend TypeScript types
(`frontend/src/types/index.ts`) byte-for-byte, so the React code can drop
straight from `mockData.ts` onto a real `fetch()` without renaming props.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
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


# ---------- voice-call dashboard reads ----------


VoiceCallScenarioLiteral = Literal["absentee", "hall_pass", "other"]
AlertStatusLiteral = Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"]
SeverityLiteral = Literal["low", "medium", "high", "critical"]


class TranscriptTurnOut(_CamelBase):
    speaker: str
    text: str
    occurred_at: datetime | None = Field(default=None, serialization_alias="occurredAt")


class VoiceCallSummaryOut(_CamelBase):
    """Card-shaped row for the admin dashboard's voice-call list.

    Excludes the full transcript; clients fetch /api/voice-calls/{id} on
    expand to see every turn.
    """

    id: UUID = Field(description="agent_messages row id")
    correlation_id: UUID = Field(serialization_alias="correlationId")
    student_id: UUID = Field(serialization_alias="studentId")
    student_name: str = Field(serialization_alias="studentName")
    alert_id: UUID | None = Field(default=None, serialization_alias="alertId")
    scenario: VoiceCallScenarioLiteral
    call_started_at: datetime = Field(serialization_alias="callStartedAt")
    call_ended_at: datetime = Field(serialization_alias="callEndedAt")
    excuse_summary: str | None = Field(default=None, serialization_alias="excuseSummary")
    parent_confirmed: bool | None = Field(default=None, serialization_alias="parentConfirmed")
    language: str | None = None
    created_at: datetime = Field(serialization_alias="createdAt")


class VoiceCallDetailOut(VoiceCallSummaryOut):
    """Full voice-call record including the per-turn transcript."""

    transcript: list[TranscriptTurnOut]


class AlertSummaryOut(_CamelBase):
    id: UUID
    student_id: UUID = Field(serialization_alias="studentId")
    student_name: str = Field(serialization_alias="studentName")
    rule_key: str = Field(serialization_alias="ruleKey")
    severity: SeverityLiteral
    status: AlertStatusLiteral
    context: dict[str, Any]
    created_at: datetime = Field(serialization_alias="createdAt")
