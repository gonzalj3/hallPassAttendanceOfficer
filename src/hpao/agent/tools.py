"""Function-calling tools the OpenAI agent can invoke.

Each tool is a thin adapter over an existing service. The docstring is
what the LLM sees as the tool description, so we write them like product
copy: terse, agent-targeted, telling it *when* to use the tool, not just
what it does. Argument descriptions come from the function-tool schema
generator and pull from the `Args:` block.

Each tool exists as a plain async function (`tool_*` names) for direct
unit testing, plus a `FunctionTool` wrapper at the bottom of the file
for the agent loop to consume. Tests import the plain functions and
call them with a synthesised `RunContextWrapper`; the agent sees only
the wrapped FunctionTools.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Any
from uuid import UUID

from agents import RunContextWrapper, function_tool
from sqlalchemy import select

from hpao.agent.context import HpaoContext
from hpao.integrations.parent_comms import dispatch_alert as dispatch_alert_impl
from hpao.models import Student
from hpao.policy.search import search_policy
from hpao.services.alerts import (
    list_alerts_for_student as list_alerts_for_student_impl,
)
from hpao.services.alerts import (
    raise_alert as raise_alert_impl,
)
from hpao.services.attendance import (
    list_attendance_for_student as list_attendance_for_student_impl,
)
from hpao.services.attendance import (
    record_attendance as record_attendance_impl,
)
from hpao.services.dispatcher import find_pending_dispatch_alerts
from hpao.services.hall_pass import (
    get_active_pass_for_student as get_active_pass_for_student_impl,
)

# ---------- read tools ----------


async def tool_get_student_attendance(
    ctx: RunContextWrapper[HpaoContext],
    student_id: str,
    since: str | None = None,
) -> dict[str, Any]:
    """Look up a student's attendance history.

    Use this whenever you need to know if a student has been showing up,
    how many days they've missed, or whether a recent absence pattern
    crosses a policy threshold. Always call this rather than guessing.

    Args:
        student_id: The student's UUID (string form).
        since: Optional ISO-8601 date (YYYY-MM-DD); only return records on
            or after this date. Omit to get the full history.
    """
    sid = UUID(student_id)
    since_date = date_type.fromisoformat(since) if since else None
    records = await list_attendance_for_student_impl(
        ctx.context.db, student_id=sid, since=since_date
    )
    return {
        "student_id": student_id,
        "since": since,
        "records": [
            {
                "class_session_id": str(r.class_session_id),
                "status": r.status,
                "source": r.source,
                "notes": r.notes,
            }
            for r in records
        ],
        "count": len(records),
    }


async def tool_get_active_hall_pass(
    ctx: RunContextWrapper[HpaoContext],
    student_id: str,
) -> dict[str, Any] | None:
    """Return the student's currently-active hall pass, or None.

    Use this when you need to know if a student is currently out of class
    -- e.g. before issuing a new pass, or when checking why an alert fired.

    Args:
        student_id: The student's UUID.
    """
    sid = UUID(student_id)
    hp = await get_active_pass_for_student_impl(ctx.context.db, student_id=sid)
    if hp is None:
        return None
    return {
        "id": str(hp.id),
        "destination": hp.destination,
        "checked_out_at": hp.checked_out_at.isoformat(),
        "expected_return_at": hp.expected_return_at.isoformat(),
        "status": hp.status,
        "reason": hp.reason,
    }


async def tool_get_open_alerts_for_student(
    ctx: RunContextWrapper[HpaoContext],
    student_id: str,
) -> list[dict[str, Any]]:
    """List a student's currently-OPEN alerts.

    Use this to ground a parent-facing reply or to decide whether the
    student is already flagged for the situation you're about to escalate.

    Args:
        student_id: The student's UUID.
    """
    sid = UUID(student_id)
    rows = await list_alerts_for_student_impl(ctx.context.db, student_id=sid)
    return [
        {
            "id": str(a.id),
            "rule_key": a.rule_key,
            "severity": a.severity,
            "created_at": a.created_at.isoformat(),
            "context": dict(a.context),
        }
        for a in rows
        if a.status == "OPEN"
    ]


async def tool_lookup_student_by_number(
    ctx: RunContextWrapper[HpaoContext],
    student_number: str,
) -> dict[str, Any] | None:
    """Resolve a school's student-number string to the UUID and basic identity.

    Use this when a teacher or parent refers to a student by their school
    ID (e.g. 'S00042'); the rest of the tool surface keys off UUIDs.

    Args:
        student_number: The school-assigned student number.
    """
    stmt = select(Student).where(Student.student_number == student_number)
    student = (await ctx.context.db.execute(stmt)).scalar_one_or_none()
    if student is None:
        return None
    return {
        "id": str(student.id),
        "student_number": student.student_number,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "grade_level": student.grade_level,
        "school_id": str(student.school_id),
    }


async def tool_query_policy(
    ctx: RunContextWrapper[HpaoContext],
    question: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Semantic search over ingested policy documents (TEA, district, school).

    Use this for nuance questions: 'is this absence excused under
    §25.087?', 'what does PfISD policy say about make-up work?'. Do NOT
    reason from training data -- the answer must be grounded in
    retrieved chunks. The deterministic rules win over anything you
    read here; policy chunks are advisory.

    Args:
        question: Natural-language question.
        limit: How many top chunks to retrieve (1-10).
    """
    results = await search_policy(
        ctx.context.db,
        ctx.context.embedder,
        question,
        limit=max(1, min(limit, 10)),
    )
    return [
        {
            "policy_id": str(chunk.policy_id),
            "text": chunk.text,
            "score": float(score),
        }
        for chunk, score in results
    ]


# ---------- write tools ----------


async def tool_record_attendance_as_agent(
    ctx: RunContextWrapper[HpaoContext],
    class_session_id: str,
    student_id: str,
    status: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """Record (or correct) a student's attendance for a class session.

    The source is fixed to AGENT so downstream audit shows it wasn't a
    teacher entry. Idempotent: same (session, student) called twice
    updates the row.

    Args:
        class_session_id: UUID of the class_session this attendance belongs to.
        student_id: Student UUID.
        status: One of PRESENT, ABSENT, TARDY, EXCUSED, UNEXCUSED.
        notes: Optional short note (e.g. parent reported a doctor's appointment).
    """
    record = await record_attendance_impl(
        ctx.context.db,
        class_session_id=UUID(class_session_id),
        student_id=UUID(student_id),
        status=status,
        source="AGENT",
        notes=notes,
    )
    return {
        "id": str(record.id),
        "status": record.status,
        "source": record.source,
        "notes": record.notes,
    }


async def tool_raise_alert_for_student(
    ctx: RunContextWrapper[HpaoContext],
    student_id: str,
    rule_key: str,
    severity: str,
    summary: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Raise an alert. Idempotent on (student, rule_key) while OPEN.

    Use sparingly: only raise alerts that match an existing rule_key the
    deterministic engine knows about, or a clearly-named ad-hoc one. The
    parent-comms agent will eventually be notified via the dispatcher.

    Args:
        student_id: Student UUID.
        rule_key: Stable rule identifier (e.g. 'hallpass.restroom.duration_exceeded').
        severity: One of low, medium, high, critical.
        summary: One-line description of why this alert is firing.
        evidence: Optional structured facts (timestamps, IDs, counts).
    """
    context_payload: dict[str, Any] = {"summary": summary}
    if evidence:
        context_payload["evidence"] = evidence
    alert = await raise_alert_impl(
        ctx.context.db,
        student_id=UUID(student_id),
        rule_key=rule_key,
        severity=severity,
        context=context_payload,
    )
    return {
        "id": str(alert.id),
        "rule_key": alert.rule_key,
        "severity": alert.severity,
        "status": alert.status,
    }


async def tool_dispatch_pending_alerts(
    ctx: RunContextWrapper[HpaoContext],
) -> dict[str, Any]:
    """Push every OPEN alert that hasn't been dispatched yet to parent-comms.

    Use after raising one or more alerts. No-op if PARENT_COMMS_URL /
    PARENT_COMMS_SECRET aren't configured -- safe to call in dev.
    """
    if not (ctx.context.parent_comms_url and ctx.context.parent_comms_secret):
        return {"dispatched": 0, "skipped": "parent_comms config missing"}

    pending = await find_pending_dispatch_alerts(ctx.context.db)
    sent = 0
    failed = 0
    for alert in pending:
        msg = await dispatch_alert_impl(
            ctx.context.db,
            alert=alert,
            base_url=ctx.context.parent_comms_url,
            secret=ctx.context.parent_comms_secret,
        )
        if msg.status == "SENT":
            sent += 1
        else:
            failed += 1
    return {"pending": len(pending), "sent": sent, "failed": failed}


# ---------- agent-facing wrappers ----------
#
# raise_alert_for_student takes `evidence: dict[str, Any]` which OpenAI's
# strict schema mode rejects (`additionalProperties` not allowed). Disable
# strict mode just for that one tool; everything else stays strict.

ALL_TOOLS = [
    function_tool(tool_get_student_attendance, name_override="get_student_attendance"),
    function_tool(tool_get_active_hall_pass, name_override="get_active_hall_pass"),
    function_tool(tool_get_open_alerts_for_student, name_override="get_open_alerts_for_student"),
    function_tool(tool_lookup_student_by_number, name_override="lookup_student_by_number"),
    function_tool(tool_query_policy, name_override="query_policy"),
    function_tool(tool_record_attendance_as_agent, name_override="record_attendance_as_agent"),
    function_tool(
        tool_raise_alert_for_student,
        name_override="raise_alert_for_student",
        strict_mode=False,
    ),
    function_tool(tool_dispatch_pending_alerts, name_override="dispatch_pending_alerts"),
]
