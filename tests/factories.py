from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4

import factory

from lizzie.models import (
    Alert,
    Class,
    ClassEnrollment,
    ClassSession,
    HallPass,
    School,
    Student,
    User,
)


class SchoolFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = School

    id = factory.LazyFunction(uuid4)
    name = factory.Faker("company")
    district = factory.Faker("city")


class StudentFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = Student

    id = factory.LazyFunction(uuid4)
    school_id = factory.LazyFunction(uuid4)
    student_number = factory.Sequence(lambda n: f"S{n:05d}")
    grade_level = "10"
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    enrolled_at = factory.LazyFunction(lambda: date(2025, 8, 15))


class UserFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = User

    id = factory.LazyFunction(uuid4)
    school_id = factory.LazyFunction(uuid4)
    email = factory.Sequence(lambda n: f"user{n}@school.edu")
    role = "TEACHER"
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class ClassFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = Class

    id = factory.LazyFunction(uuid4)
    school_id = factory.LazyFunction(uuid4)
    teacher_id = factory.LazyFunction(uuid4)
    name = factory.Faker("catch_phrase")
    subject = "math"
    period = factory.Sequence(lambda n: str((n % 8) + 1))
    room = factory.Sequence(lambda n: f"B-{n:03d}")


class ClassEnrollmentFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = ClassEnrollment

    id = factory.LazyFunction(uuid4)
    class_id = factory.LazyFunction(uuid4)
    student_id = factory.LazyFunction(uuid4)
    enrolled_at = factory.LazyFunction(lambda: date(2025, 8, 15))


class ClassSessionFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = ClassSession

    id = factory.LazyFunction(uuid4)
    class_id = factory.LazyFunction(uuid4)
    date = factory.LazyFunction(lambda: date(2025, 9, 4))
    scheduled_start = factory.LazyFunction(lambda: time(9, 0))
    scheduled_end = factory.LazyFunction(lambda: time(9, 50))


class HallPassFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = HallPass

    id = factory.LazyFunction(uuid4)
    student_id = factory.LazyFunction(uuid4)
    originating_class_session_id = factory.LazyFunction(uuid4)
    destination = "RESTROOM"
    reason = None
    checked_out_at = factory.LazyFunction(lambda: datetime.now(UTC))
    expected_return_at = factory.LazyFunction(lambda: datetime.now(UTC) + timedelta(minutes=15))
    checked_in_at = None
    status = "ACTIVE"
    issued_by = factory.LazyFunction(uuid4)


class AlertFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = Alert

    id = factory.LazyFunction(uuid4)
    student_id = factory.LazyFunction(uuid4)
    rule_key = "hallpass.restroom.duration_exceeded"
    severity = "high"
    status = "OPEN"
    context = factory.LazyFunction(dict)
    acknowledged_by = None
    acknowledged_at = None
    resolved_at = None
