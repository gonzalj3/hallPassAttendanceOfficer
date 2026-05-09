from datetime import date, time
from uuid import uuid4

import factory

from hpao.models import Class, ClassEnrollment, ClassSession, School, Student, User


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
