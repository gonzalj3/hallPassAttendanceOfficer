"""Pydantic request/response schemas for the agent boundary.

These are the on-the-wire shape contracts between HPAO and the
parent-comms agent. CLAUDE.md is the source of truth; if a field
changes here, update CLAUDE.md too.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- inbound: parent-comms -> HPAO ----------


class ParentMessageIn(_Base):
    """A parent reached out to parent-comms; they're logging it with us."""

    correlation_id: UUID
    student_id: UUID
    guardian_external_id: str | None = Field(
        default=None,
        description=(
            "Optional external id from parent-comms's guardian table; HPAO "
            "doesn't own guardians, so we just record what they tell us."
        ),
    )
    channel: str = Field(description="sms | email | call | other")
    received_at: datetime
    body: str = Field(description="The parent's message text, verbatim.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParentResponseIn(_Base):
    """A reply from a parent in response to a previous outbound notification."""

    correlation_id: UUID
    student_id: UUID
    in_reply_to: UUID = Field(description="correlation_id of the original outbound message.")
    channel: str
    received_at: datetime
    body: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class InboundAck(_Base):
    """Standard ack returned for both inbound endpoints."""

    accepted: bool = True
    agent_message_id: UUID
    correlation_id: UUID
    duplicate: bool = Field(
        default=False,
        description=(
            "True when the same correlation_id was already logged. The endpoint "
            "is idempotent, so duplicates are a no-op rather than an error."
        ),
    )


# ---------- outbound: HPAO -> parent-comms ----------


class OutboundGuardianHint(_Base):
    """Best-effort guardian metadata HPAO has for the parent-comms agent.

    Parent-comms can override based on its own opt-out / preference state.
    """

    id: UUID | None = None
    name: str | None = None
    preferred_channel: str | None = None  # sms | email | call
    preferred_language: str | None = None  # en | es


class OutboundContext(_Base):
    rule_key: str
    summary: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class OutboundNotification(_Base):
    """The shape HPAO POSTs to {parent_comms_base}/notifications.

    See CLAUDE.md "HPAO -> parent-comms (outbound webhook)" for the spec.
    """

    correlation_id: UUID
    event: str = Field(description="alert.raised | other future events")
    severity: str = Field(description="low | medium | high | critical")
    student_id: UUID
    guardians: list[OutboundGuardianHint] = Field(default_factory=list)
    context: OutboundContext
    intent: str = Field(description="notify | request_info | request_exemption_review")


# ---------- read-side: parent-comms -> HPAO ----------


class StudentContextOut(_Base):
    """Snapshot of a student that parent-comms uses to ground its replies.

    Trimmed to what an agent actually needs to draft a parent-facing message
    -- not a full DB dump.
    """

    student_id: UUID
    student_number: str
    grade_level: str
    first_name: str
    last_name: str
    school_id: UUID

    attendance_summary: AttendanceSummary
    active_hall_passes: list[ActiveHallPassOut]
    open_alerts: list[OpenAlertOut]


class AttendanceSummary(_Base):
    days_present: int
    days_absent: int
    days_tardy: int
    days_excused: int
    days_unexcused: int
    days_total: int


class ActiveHallPassOut(_Base):
    id: UUID
    destination: str
    checked_out_at: datetime
    expected_return_at: datetime
    minutes_elapsed: float


class OpenAlertOut(_Base):
    id: UUID
    rule_key: str
    severity: str
    created_at: datetime
    context: dict[str, Any]


# Pydantic v2 needs explicit forward-ref resolution when a model references
# another defined later in the file.
StudentContextOut.model_rebuild()


# ---------- attendance summary helper for the GET endpoint ----------


class StudentContextRequest(_Base):
    """Optional `since` date filter on the attendance summary."""

    since: date | None = None


# ---------- inbound: outbound-voice-agent -> HPAO ----------


class TranscriptTurn(_Base):
    """One turn from a voice agent transcript."""

    speaker: str = Field(description="agent | guardian | system")
    text: str
    occurred_at: datetime | None = None


class VoiceCallIn(_Base):
    """The outbound voice agent reports a finished parent call.

    Idempotent on `correlation_id`. The endpoint persists the full record
    into agent_messages (counterparty=voice_agent, direction=INBOUND) and
    publishes a voice_call.completed realtime event so admin dashboards
    can surface the conversation immediately.
    """

    correlation_id: UUID
    student_id: UUID
    alert_id: UUID | None = Field(
        default=None,
        description=(
            "Alert that triggered the call, when known. Lets admins jump from "
            "a transcript card straight to the underlying threshold breach."
        ),
    )
    scenario: str = Field(description="absentee | hall_pass | other")
    call_started_at: datetime
    call_ended_at: datetime
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    excuse_summary: str | None = Field(
        default=None,
        description=(
            "Short summary of the guardian's stated reason, e.g. 'Doctor "
            "appointment, returning Wednesday'. Voice agent fills this in "
            "after the conversation; null when no excuse was captured."
        ),
    )
    parent_confirmed: bool | None = None
    language: str | None = Field(default=None, description="BCP-47 / ISO 639-1, e.g. 'en' or 'es'.")
    metadata: dict[str, Any] = Field(default_factory=dict)
