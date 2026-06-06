"""Admin-only endpoints.

The single route here -- ``DELETE /api/admin/students/{id}`` -- exists
to make Texas Student Privacy Act (TEC §32.155) deletion requests a
30-second self-service action instead of a database ticket. Demo data
today, real student rows on a future pilot; same code path either way.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from lizzie.auth.dependencies import CurrentUser, require_role
from lizzie.models import Alert, ClassEnrollment, HallPass, Student
from lizzie.services.audit import write_audit


def _get_session() -> AsyncSession:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="DB session provider not configured",
    )


SessionDep = Annotated[AsyncSession, Depends(_get_session)]
AdminDep = Annotated[CurrentUser, Depends(require_role("ADMIN"))]


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.delete(
    "/students/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_student(
    student_id: UUID,
    db: SessionDep,
    actor: AdminDep,
) -> None:
    """Hard-delete a student and every row that references them.

    Cascade order: alerts -> hall_passes -> class_enrollments -> student.
    The audit row is written BEFORE the delete so it survives even if a
    later step fails (the FK on audit_log.user_id is ON DELETE SET NULL,
    so the auditor's account can vanish without losing the record).
    """
    student = await db.get(Student, student_id)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"student {student_id} not found",
        )

    await write_audit(
        db,
        user=actor,
        action="student.delete",
        target_type="student",
        target_id=student_id,
        context={
            "student_number": student.student_number,
            "first_name": student.first_name,
            "last_name": student.last_name,
        },
    )

    await db.execute(delete(Alert).where(Alert.student_id == student_id))
    await db.execute(delete(HallPass).where(HallPass.student_id == student_id))
    await db.execute(delete(ClassEnrollment).where(ClassEnrollment.student_id == student_id))
    await db.delete(student)
    await db.flush()


def mount(
    app: FastAPI,
    *,
    session_provider: Callable[[], Any] | None = None,
) -> None:
    app.include_router(router)
    if session_provider is not None:
        app.dependency_overrides[_get_session] = session_provider
