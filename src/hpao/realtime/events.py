from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["low", "medium", "high", "critical"]
AttendanceStatus = Literal["PRESENT", "ABSENT", "TARDY", "EXCUSED", "UNEXCUSED"]
Destination = Literal["RESTROOM", "NURSE", "COUNSELOR", "OFFICE", "OTHER", "HALLWAY", "CLASSROOM"]


class _EventBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: UUID
    occurred_at: datetime
    school_id: UUID
    student_id: UUID


class AttendanceRecorded(_EventBase):
    event: Literal["attendance.recorded"] = "attendance.recorded"
    class_id: UUID
    class_session_id: UUID
    status: AttendanceStatus
    source: str
    recorded_by: UUID


class HallpassIssued(_EventBase):
    event: Literal["hallpass.issued"] = "hallpass.issued"
    hall_pass_id: UUID
    class_id: UUID | None = None
    class_session_id: UUID | None = None
    destination: Destination
    expected_return_at: datetime
    issued_by: UUID


class HallpassReturned(_EventBase):
    event: Literal["hallpass.returned"] = "hallpass.returned"
    hall_pass_id: UUID
    class_id: UUID | None = None
    checked_in_at: datetime


class HallpassOverdue(_EventBase):
    event: Literal["hallpass.overdue"] = "hallpass.overdue"
    hall_pass_id: UUID
    class_id: UUID | None = None
    expected_return_at: datetime
    minutes_elapsed: int = Field(ge=0)


class AlertRaised(_EventBase):
    event: Literal["alert.raised"] = "alert.raised"
    alert_id: UUID
    class_id: UUID | None = None
    rule_key: str
    severity: Severity
    summary: str
    evidence: dict[str, Any] = Field(default_factory=dict)


RealtimeEvent = Annotated[
    AttendanceRecorded | HallpassIssued | HallpassReturned | HallpassOverdue | AlertRaised,
    Field(discriminator="event"),
]


def channels_for(event: RealtimeEvent) -> list[str]:
    """Derive pg_notify channels an event fans out to.

    Every event publishes to its school and student channels. Class scope is
    added when the event is tied to a class (attendance always; hall passes
    and alerts when a class context is set).
    """
    channels = [f"school:{event.school_id}", f"student:{event.student_id}"]
    class_id = getattr(event, "class_id", None)
    if class_id is not None:
        channels.append(f"class:{class_id}")
    return channels
