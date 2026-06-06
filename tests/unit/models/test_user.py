from uuid import uuid4

from lizzie.models import USER_ROLES, User


def test_user_construction() -> None:
    school_id = uuid4()
    u = User(
        school_id=school_id,
        email="ms.garcia@school.edu",
        role="TEACHER",
        first_name="Maria",
        last_name="Garcia",
    )
    assert u.school_id == school_id
    assert u.email == "ms.garcia@school.edu"
    assert u.role == "TEACHER"
    assert u.first_name == "Maria"


def test_user_roles_constant() -> None:
    assert "TEACHER" in USER_ROLES
    assert "ADMIN" in USER_ROLES
    assert "COUNSELOR" in USER_ROLES
    assert "NURSE" in USER_ROLES
    assert len(USER_ROLES) == 4


def test_user_repr_includes_role_and_name() -> None:
    u = User(
        school_id=uuid4(),
        email="x@y.z",
        role="ADMIN",
        first_name="Alex",
        last_name="Park",
    )
    rep = repr(u)
    assert "ADMIN" in rep
    assert "Park" in rep
