"""Smoke tests for the agent factory.

The actual LLM loop is network-bound; we don't run that in the gate.
But we do confirm that the Agent builds, has the expected tool surface,
and that the tool names the LLM sees are stable (a typo here would
break parent-comms / staff workflows that key off rule_keys built into
the prompts).
"""

from hpao.agent.officer import make_officer
from hpao.agent.tools import ALL_TOOLS


def test_make_officer_builds_with_default_model() -> None:
    officer = make_officer()
    assert officer.name == "HPAO Attendance Officer"
    assert officer.tools  # non-empty


def test_make_officer_carries_all_tools() -> None:
    officer = make_officer()
    assert len(officer.tools) == len(ALL_TOOLS)


def test_officer_tool_names_are_stable() -> None:
    """If a tool is renamed, the prompt + downstream agents need updating
    in lockstep -- this test fails loudly when that happens."""
    officer = make_officer()
    names = {t.name for t in officer.tools}  # type: ignore[attr-defined]
    assert names == {
        "get_student_attendance",
        "get_active_hall_pass",
        "get_open_alerts_for_student",
        "lookup_student_by_number",
        "query_policy",
        "record_attendance_as_agent",
        "raise_alert_for_student",
        "dispatch_pending_alerts",
    }


def test_officer_accepts_custom_model() -> None:
    officer = make_officer(model="gpt-4o")
    assert officer.model == "gpt-4o"
