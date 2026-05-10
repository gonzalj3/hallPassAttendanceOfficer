"""Inbound endpoints the parent-comms agent calls on HPAO.

All POST endpoints require an HMAC signature in `X-HPAO-Signature`. The
GET endpoint (student-context) is also signed for consistency with the
other-direction calls.

This module exposes a `router` and a `mount(app)` helper. The other agent's
make_app() factory (or any FastAPI app the project chooses) can call
`mount(app)` to add the agent routes alongside the realtime WebSocket
routes.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.api.security import SIGNATURE_HEADER, verify
from hpao.models import (
    ATTENDANCE_STATUSES,
    Alert,
    AttendanceRecord,
    HallPass,
    Student,
)
from hpao.realtime.events import VoiceCallCompleted
from hpao.realtime.postgres import PgNotifyPublisher
from hpao.schemas.agent import (
    ActiveHallPassOut,
    AttendanceSummary,
    InboundAck,
    OpenAlertOut,
    ParentMessageIn,
    ParentResponseIn,
    StudentContextOut,
    VoiceCallIn,
)
from hpao.services.agent_messages import log_inbound

# Type alias for the session-provider callable the app injects via the
# router. We don't bind to a concrete dependency here so the same router
# can be tested with a transactional session and run in production with a
# request-scoped one.
SessionProvider = Callable[[], Awaitable[AsyncSession]]


COUNTERPARTY = "parent_comms"
COUNTERPARTY_VOICE_AGENT = "voice_agent"


# ---------- dependency factories ----------


def _get_secret() -> str | None:
    """Override in app wiring via app.dependency_overrides.

    Returns None when no shared secret is configured. In that case the
    agent boundary skips HMAC verification entirely -- intended for
    hackathon / local-dev use only. Set ``PARENT_COMMS_SECRET`` to
    re-enable signing.
    """
    return None


def _get_session() -> AsyncSession:
    """Override in tests / app wiring via app.dependency_overrides."""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="DB session provider not configured",
    )


SecretDep = Annotated[str | None, Depends(_get_secret)]
SessionDep = Annotated[AsyncSession, Depends(_get_session)]


async def _verified_body(request: Request, secret: SecretDep) -> bytes:
    """Read raw body, verify HMAC, return body bytes for downstream parsing.

    FastAPI consumes the body when it parses a Pydantic model from JSON, so
    we read it here first, verify, then re-inject so the next parser can
    read again. (Standard pattern for HMAC over raw body in FastAPI.)

    When ``secret`` is unset (hackathon mode) verification is skipped --
    the endpoint becomes publicly callable, so leave the secret set in
    any environment with real data.
    """
    body = await request.body()
    if not secret:
        request._body = body
        return body
    sig = request.headers.get(SIGNATURE_HEADER)
    if not verify(secret, body, sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid HMAC signature",
        )
    # Make body re-readable downstream
    request._body = body
    return body


VerifiedBodyDep = Annotated[bytes, Depends(_verified_body)]


# ---------- router ----------


router = APIRouter(prefix="/v1/agent", tags=["agent"])


@router.post(
    "/inbound/parent-message",
    response_model=InboundAck,
    status_code=status.HTTP_200_OK,
)
async def inbound_parent_message(
    payload: ParentMessageIn,
    _verified: VerifiedBodyDep,
    db: SessionDep,
) -> InboundAck:
    """A parent reached out to parent-comms; they're logging it with us."""
    msg, duplicate = await log_inbound(
        db,
        counterparty=COUNTERPARTY,
        correlation_id=payload.correlation_id,
        payload=payload.model_dump(mode="json"),
        student_id=payload.student_id,
    )
    return InboundAck(
        accepted=True,
        agent_message_id=msg.id,
        correlation_id=payload.correlation_id,
        duplicate=duplicate,
    )


@router.post(
    "/inbound/parent-response",
    response_model=InboundAck,
    status_code=status.HTTP_200_OK,
)
async def inbound_parent_response(
    payload: ParentResponseIn,
    _verified: VerifiedBodyDep,
    db: SessionDep,
) -> InboundAck:
    """A parent reply to a previous outbound notification."""
    msg, duplicate = await log_inbound(
        db,
        counterparty=COUNTERPARTY,
        correlation_id=payload.correlation_id,
        payload=payload.model_dump(mode="json"),
        student_id=payload.student_id,
    )
    return InboundAck(
        accepted=True,
        agent_message_id=msg.id,
        correlation_id=payload.correlation_id,
        duplicate=duplicate,
    )


@router.post(
    "/inbound/voice-call",
    response_model=InboundAck,
    status_code=status.HTTP_200_OK,
)
async def inbound_voice_call(
    payload: VoiceCallIn,
    _verified: VerifiedBodyDep,
    db: SessionDep,
) -> InboundAck:
    """The outbound voice agent finished a parent call.

    Persists the full record (transcript + metadata) into agent_messages
    under counterparty=voice_agent and publishes voice_call.completed over
    realtime so admin dashboards can surface the conversation immediately.
    Idempotent on `correlation_id`.
    """
    msg, duplicate = await log_inbound(
        db,
        counterparty=COUNTERPARTY_VOICE_AGENT,
        correlation_id=payload.correlation_id,
        payload=payload.model_dump(mode="json"),
        student_id=payload.student_id,
        alert_id=payload.alert_id,
    )

    if not duplicate:
        student = await db.get(Student, payload.student_id)
        if student is None:
            # FK on agent_messages.student_id would have rejected the insert,
            # so this is unreachable in practice. Defensive in case future
            # callers nullify the FK.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"student {payload.student_id} not found",
            )
        event = VoiceCallCompleted(
            event_id=uuid4(),
            occurred_at=datetime.now(tz=payload.call_ended_at.tzinfo),
            school_id=student.school_id,
            student_id=payload.student_id,
            agent_message_id=msg.id,
            correlation_id=payload.correlation_id,
            alert_id=payload.alert_id,
            scenario=payload.scenario,
            call_started_at=payload.call_started_at,
            call_ended_at=payload.call_ended_at,
            parent_confirmed=payload.parent_confirmed,
            excuse_summary=payload.excuse_summary,
            language=payload.language,
        )
        conn = await db.connection()
        await PgNotifyPublisher(conn).publish(event)

    return InboundAck(
        accepted=True,
        agent_message_id=msg.id,
        correlation_id=payload.correlation_id,
        duplicate=duplicate,
    )


@router.get(
    "/student-context/{student_id}",
    response_model=StudentContextOut,
)
async def student_context(
    student_id: UUID,
    request: Request,
    secret: SecretDep,
    db: SessionDep,
    since: date | None = None,
) -> StudentContextOut:
    """Snapshot used by parent-comms to ground its parent-facing replies.

    Signed like the POST endpoints; with no body, the signature covers the
    empty bytes -- still authenticates the caller via the shared secret.
    """
    body = await request.body()
    if secret:
        sig = request.headers.get(SIGNATURE_HEADER)
        if not verify(secret, body, sig):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid HMAC signature",
            )

    student = await db.get(Student, student_id)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"student {student_id} not found",
        )

    summary = await _attendance_summary(db, student_id=student_id, since=since)
    active_passes = await _active_hall_passes(db, student_id=student_id)
    open_alerts = await _open_alerts(db, student_id=student_id)

    return StudentContextOut(
        student_id=student.id,
        student_number=student.student_number,
        grade_level=student.grade_level,
        first_name=student.first_name,
        last_name=student.last_name,
        school_id=student.school_id,
        attendance_summary=summary,
        active_hall_passes=active_passes,
        open_alerts=open_alerts,
    )


# ---------- helpers ----------


async def _attendance_summary(
    db: AsyncSession, *, student_id: UUID, since: date | None
) -> AttendanceSummary:
    stmt = select(AttendanceRecord.status, func.count()).where(
        AttendanceRecord.student_id == student_id
    )
    if since is not None:
        from hpao.models import ClassSession

        stmt = stmt.join(ClassSession, AttendanceRecord.class_session_id == ClassSession.id).where(
            ClassSession.date >= since
        )
    stmt = stmt.group_by(AttendanceRecord.status)

    counts: dict[str, int] = dict.fromkeys(ATTENDANCE_STATUSES, 0)
    for status_value, count in (await db.execute(stmt)).all():
        counts[status_value] = count

    return AttendanceSummary(
        days_present=counts["PRESENT"],
        days_absent=counts["ABSENT"],
        days_tardy=counts["TARDY"],
        days_excused=counts["EXCUSED"],
        days_unexcused=counts["UNEXCUSED"],
        days_total=sum(counts.values()),
    )


async def _active_hall_passes(db: AsyncSession, *, student_id: UUID) -> list[ActiveHallPassOut]:
    stmt = select(HallPass).where(
        HallPass.student_id == student_id,
        HallPass.status == "ACTIVE",
    )
    rows = (await db.execute(stmt)).scalars().all()
    out: list[ActiveHallPassOut] = []
    for hp in rows:
        now = datetime.now(tz=hp.checked_out_at.tzinfo)
        elapsed = (now - hp.checked_out_at).total_seconds() / 60
        out.append(
            ActiveHallPassOut(
                id=hp.id,
                destination=hp.destination,
                checked_out_at=hp.checked_out_at,
                expected_return_at=hp.expected_return_at,
                minutes_elapsed=round(elapsed, 1),
            )
        )
    return out


async def _open_alerts(db: AsyncSession, *, student_id: UUID) -> list[OpenAlertOut]:
    stmt = (
        select(Alert)
        .where(Alert.student_id == student_id, Alert.status == "OPEN")
        .order_by(Alert.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        OpenAlertOut(
            id=a.id,
            rule_key=a.rule_key,
            severity=a.severity,
            created_at=a.created_at,
            context=dict(a.context),
        )
        for a in rows
    ]


# ---------- mount helper ----------


def mount(
    app: FastAPI,
    *,
    session_provider: Callable[[], Any] | None = None,
    secret: str | None = None,
) -> None:
    """Wire the agent router into a FastAPI app.

    Pass `session_provider` and `secret` to bind the dependency overrides;
    or call `app.dependency_overrides[_get_session] = ...` /
    `app.dependency_overrides[_get_secret] = ...` directly for finer control.
    """
    app.include_router(router)
    if session_provider is not None:
        app.dependency_overrides[_get_session] = session_provider
    if secret is not None:
        app.dependency_overrides[_get_secret] = lambda: secret
