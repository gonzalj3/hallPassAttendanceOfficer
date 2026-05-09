from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4

import factory

from hpao.models import (
    AgentMessage,
    Alert,
    AttendanceRecord,
    Class,
    ClassEnrollment,
    ClassSession,
    HallPass,
    Policy,
    PolicyChunk,
    PolicyRule,
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
    school_id = factory.LazyFunction(uuid4)  # tests should override with a real school's id
    student_number = factory.Sequence(lambda n: f"S{n:05d}")
    grade_level = "10"
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    enrolled_at = factory.LazyFunction(lambda: date(2025, 8, 15))


class UserFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = User

    id = factory.LazyFunction(uuid4)
    school_id = factory.LazyFunction(uuid4)  # override with a real school's id
    email = factory.Sequence(lambda n: f"user{n}@school.edu")
    role = "TEACHER"
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class ClassFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = Class

    id = factory.LazyFunction(uuid4)
    school_id = factory.LazyFunction(uuid4)  # override
    teacher_id = factory.LazyFunction(uuid4)  # override
    name = factory.Faker("catch_phrase")
    subject = "math"
    period = factory.Sequence(lambda n: str((n % 8) + 1))
    room = factory.Sequence(lambda n: f"B-{n:03d}")


class ClassEnrollmentFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = ClassEnrollment

    id = factory.LazyFunction(uuid4)
    class_id = factory.LazyFunction(uuid4)  # override
    student_id = factory.LazyFunction(uuid4)  # override
    enrolled_at = factory.LazyFunction(lambda: date(2025, 8, 15))


class ClassSessionFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = ClassSession

    id = factory.LazyFunction(uuid4)
    class_id = factory.LazyFunction(uuid4)  # override
    date = factory.LazyFunction(lambda: date(2025, 9, 4))
    scheduled_start = factory.LazyFunction(lambda: time(9, 0))
    scheduled_end = factory.LazyFunction(lambda: time(9, 50))


class AttendanceRecordFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = AttendanceRecord

    id = factory.LazyFunction(uuid4)
    class_session_id = factory.LazyFunction(uuid4)  # override
    student_id = factory.LazyFunction(uuid4)  # override
    status = "PRESENT"
    source = "TEACHER"
    recorded_by = None
    notes = None


class HallPassFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = HallPass

    id = factory.LazyFunction(uuid4)
    student_id = factory.LazyFunction(uuid4)  # override
    originating_class_session_id = factory.LazyFunction(uuid4)  # override
    destination = "RESTROOM"
    reason = None
    checked_out_at = factory.LazyFunction(lambda: datetime.now(UTC))
    expected_return_at = factory.LazyFunction(lambda: datetime.now(UTC) + timedelta(minutes=15))
    checked_in_at = None
    status = "ACTIVE"
    issued_by = factory.LazyFunction(uuid4)  # override


class PolicyFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = Policy

    id = factory.LazyFunction(uuid4)
    scope = "tea"
    name = factory.Sequence(lambda n: f"Policy {n}")
    source_url = None
    version = "v1"
    effective_date = factory.LazyFunction(lambda: date(2025, 8, 1))


class PolicyChunkFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = PolicyChunk

    id = factory.LazyFunction(uuid4)
    policy_id = factory.LazyFunction(uuid4)  # override with a real policy id
    text = factory.Sequence(lambda n: f"Chunk text {n}")
    embedding = None  # populated in Phase 5c


class PolicyRuleFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = PolicyRule

    id = factory.LazyFunction(uuid4)
    policy_id = factory.LazyFunction(uuid4)  # override
    rule_key = factory.Sequence(lambda n: f"test.rule.{n}")
    expression = factory.LazyFunction(lambda: {"op": "noop"})
    threshold = None
    severity = "medium"


class AlertFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = Alert

    id = factory.LazyFunction(uuid4)
    student_id = factory.LazyFunction(uuid4)  # override
    rule_key = "hallpass.restroom.duration_exceeded"
    severity = "high"
    status = "OPEN"
    context = factory.LazyFunction(dict)
    acknowledged_by = None
    acknowledged_at = None
    resolved_at = None


class AgentMessageFactory(factory.Factory):  # type: ignore[misc]
    class Meta:
        model = AgentMessage

    id = factory.LazyFunction(uuid4)
    direction = "INBOUND"
    counterparty = "parent_comms"
    correlation_id = factory.LazyFunction(uuid4)
    student_id = None
    alert_id = None
    payload = factory.LazyFunction(dict)
    status = "RECEIVED"
    error = None
    sent_at = None
