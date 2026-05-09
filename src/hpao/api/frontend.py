"""Browser-facing REST surface for the React/Vite frontend.

Plain JSON, no HMAC. Composes the existing service layer (Phase 3 hall
pass service, Phase 1c models). The realtime WS endpoint at /v1/realtime
is the live-update channel; this router covers the read-and-write CRUD
the UI drives directly.

Routes (all prefixed `/api`):
  GET  /sessions                       — today's class sessions
  GET  /sessions/{id}/students         — roster + active passes
  POST /hall-passes                    — issue
  POST /hall-passes/{id}/return        — check in
  GET  /hall-passes                    — list, optional status / sessionId filter
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import (
    Class,
    ClassEnrollment,
    ClassSession,
    HallPass,
    Student,
)
from hpao.schemas.frontend import (
    ClassPeriodOut,
    HallPassOut,
    HallPassStatusLiteral,
    IssueHallPassIn,
    RosterOut,
    StudentOut,
)
from hpao.services.hall_pass import (
    HallPassConflictError,
    HallPassValidationError,
    check_in_pass,
    issue_pass,
)


def _get_session() -> AsyncSession:
    """Override in app wiring via app.dependency_overrides."""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="DB session provider not configured",
    )


SessionDep = Annotated[AsyncSession, Depends(_get_session)]


router = APIRouter(prefix="/api", tags=["frontend"])


# ---------- helpers ----------


def _grade_level_to_int(raw: str) -> int:
    """Backend stores K-12 grades as strings; frontend's TS type is `number`."""
    return int(raw) if raw.isdigit() else 0


def _student_to_out(student: Student) -> StudentOut:
    return StudentOut(
        id=student.id,
        name=f"{student.first_name} {student.last_name}",
        student_number=student.student_number,
        grade_level=_grade_level_to_int(student.grade_level),
    )


def _format_time(t: time) -> str:
    """Produce the zero-padded "08:30 AM" shape the existing UI mocks use."""
    return t.strftime("%I:%M %p")


def _classify_period(
    *,
    period: str,
    name: str,
    start: time,
    end: time,
    now_local: time,
) -> str:
    """Map a session into one of frontend's four `type` values.

    Single-school hackathon, single-timezone demo: "suggested" is whichever
    session contains the current local time. Specially-named periods get
    their own buckets so the frontend can style them differently.
    """
    if start <= now_local <= end:
        return "suggested"
    if "lunch" in period.lower() or "lunch" in name.lower():
        return "lunch"
    if "advisory" in period.lower() or "advisory" in name.lower():
        return "advisory"
    return "regular"


async def _student_count_for_class(db: AsyncSession, class_id: UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(ClassEnrollment)
        .where(ClassEnrollment.class_id == class_id)
    )
    return int((await db.execute(stmt)).scalar_one())


async def _hall_pass_to_out(db: AsyncSession, hp: HallPass) -> HallPassOut:
    student = await db.get(Student, hp.student_id)
    name = f"{student.first_name} {student.last_name}" if student else "(unknown)"
    return HallPassOut(
        id=hp.id,
        student_id=hp.student_id,
        student_name=name,
        destination=hp.destination,
        checked_out_at=hp.checked_out_at,
        expected_return_at=hp.expected_return_at,
        checked_in_at=hp.checked_in_at,
        status=hp.status,
    )


async def _session_to_period(
    db: AsyncSession,
    session: ClassSession,
    *,
    now_local: time,
) -> ClassPeriodOut:
    cls = await db.get(Class, session.class_id)
    if cls is None:  # FK enforces existence; defensive for type checkers
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"class {session.class_id} missing for session {session.id}",
        )
    student_count = await _student_count_for_class(db, cls.id)
    return ClassPeriodOut(
        id=session.id,
        class_id=cls.id,
        school_id=cls.school_id,
        name=cls.name,
        subject=cls.subject or "",
        period=cls.period,
        start_time=_format_time(session.scheduled_start),
        end_time=_format_time(session.scheduled_end),
        room=cls.room or "",
        teacher_id=cls.teacher_id,
        student_count=student_count,
        type=_classify_period(
            period=cls.period,
            name=cls.name,
            start=session.scheduled_start,
            end=session.scheduled_end,
            now_local=now_local,
        ),
    )


def _today_local() -> tuple[date, time]:
    """School-local 'now' — single-school hackathon assumes server local time."""
    now = datetime.now()
    return now.date(), now.time()


# ---------- routes ----------


@router.get("/sessions", response_model=list[ClassPeriodOut], response_model_by_alias=True)
async def list_sessions(db: SessionDep) -> list[ClassPeriodOut]:
    """Today's class sessions for the demo school.

    Frontend `id` is the ClassSession id, not the Class id — that's what
    /sessions/{id}/students and POST /hall-passes both key off, so a single
    URL parameter survives the whole flow.
    """
    today, now_local = _today_local()
    stmt = select(ClassSession).where(ClassSession.date == today)
    sessions = list((await db.execute(stmt)).scalars().all())
    return [await _session_to_period(db, s, now_local=now_local) for s in sessions]


@router.get(
    "/sessions/{session_id}/students",
    response_model=RosterOut,
    response_model_by_alias=True,
)
async def get_roster(session_id: UUID, db: SessionDep) -> RosterOut:
    session = await db.get(ClassSession, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"session {session_id} not found"
        )
    _, now_local = _today_local()
    period = await _session_to_period(db, session, now_local=now_local)

    student_stmt = (
        select(Student)
        .join(ClassEnrollment, ClassEnrollment.student_id == Student.id)
        .where(ClassEnrollment.class_id == session.class_id)
        .order_by(Student.last_name, Student.first_name)
    )
    students = list((await db.execute(student_stmt)).scalars().all())

    pass_stmt = (
        select(HallPass)
        .where(
            HallPass.originating_class_session_id == session_id,
            HallPass.status == "ACTIVE",
        )
        .order_by(HallPass.checked_out_at)
    )
    active = list((await db.execute(pass_stmt)).scalars().all())

    return RosterOut(
        session=period,
        students=[_student_to_out(s) for s in students],
        active_passes=[await _hall_pass_to_out(db, hp) for hp in active],
    )


@router.post(
    "/hall-passes",
    response_model=HallPassOut,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def issue_hall_pass(payload: IssueHallPassIn, db: SessionDep) -> HallPassOut:
    """Issue a pass. Teacher (`issued_by`) is inferred from the class_session."""
    session = await db.get(ClassSession, payload.session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"session {payload.session_id} not found"
        )
    cls = await db.get(Class, session.class_id)
    if cls is None:  # FK guarantees this; defensive
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="class FK")

    try:
        hp = await issue_pass(
            db,
            student_id=payload.student_id,
            originating_class_session_id=payload.session_id,
            destination=payload.destination,
            issued_by=cls.teacher_id,
            reason=payload.reason,
            duration_minutes=payload.duration_minutes,
        )
    except HallPassConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except HallPassValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    return await _hall_pass_to_out(db, hp)


@router.post(
    "/hall-passes/{pass_id}/return",
    response_model=HallPassOut,
    response_model_by_alias=True,
)
async def return_hall_pass(pass_id: UUID, db: SessionDep) -> HallPassOut:
    try:
        hp = await check_in_pass(db, pass_id=pass_id)
    except HallPassValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    return await _hall_pass_to_out(db, hp)


@router.get("/hall-passes", response_model=list[HallPassOut], response_model_by_alias=True)
async def list_hall_passes(
    db: SessionDep,
    status_filter: HallPassStatusLiteral | None = None,
    session_id: UUID | None = None,
) -> list[HallPassOut]:
    stmt = select(HallPass)
    if status_filter is not None:
        stmt = stmt.where(HallPass.status == status_filter)
    if session_id is not None:
        stmt = stmt.where(HallPass.originating_class_session_id == session_id)
    stmt = stmt.order_by(HallPass.checked_out_at.desc())
    rows = list((await db.execute(stmt)).scalars().all())
    return [await _hall_pass_to_out(db, hp) for hp in rows]


# ---------- mount helper ----------


def mount(
    app: FastAPI,
    *,
    session_provider: Callable[[], Any] | None = None,
) -> None:
    app.include_router(router)
    if session_provider is not None:
        app.dependency_overrides[_get_session] = session_provider
