from datetime import date
from uuid import uuid4

import factory

from hpao.models import School, Student


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
