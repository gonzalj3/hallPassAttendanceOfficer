"""Pure unit tests for hall pass duration defaults.

The 15-minute restroom default is the trigger for the 15-min on-duty admin
alert in Phase 6. If it changes, that alert's expected behavior changes too.
"""

from hpao.services.hall_pass import (
    DEFAULT_DURATION_MINUTES,
    default_duration_minutes,
)


def test_restroom_defaults_to_15_minutes() -> None:
    assert default_duration_minutes("RESTROOM") == 15


def test_nurse_defaults_to_30_minutes() -> None:
    assert default_duration_minutes("NURSE") == 30


def test_counselor_defaults_to_30_minutes() -> None:
    assert default_duration_minutes("COUNSELOR") == 30


def test_office_defaults_to_30_minutes() -> None:
    assert default_duration_minutes("OFFICE") == 30


def test_other_defaults_to_15_minutes() -> None:
    assert default_duration_minutes("OTHER") == 15


def test_unknown_destination_falls_back_to_15() -> None:
    """Forward compatibility: a destination that's not in the table gets a
    safe 15-minute default rather than a long timeout."""
    assert default_duration_minutes("CAFETERIA") == 15


def test_default_durations_table_covers_all_known_destinations() -> None:
    """Tripwire: if HALL_PASS_DESTINATIONS gains a member, this test fails
    until DEFAULT_DURATION_MINUTES is updated alongside it."""
    from hpao.models import HALL_PASS_DESTINATIONS

    missing = set(HALL_PASS_DESTINATIONS) - set(DEFAULT_DURATION_MINUTES)
    assert not missing, f"missing default durations for: {missing}"
