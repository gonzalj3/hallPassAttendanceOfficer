"""Default rule specs HPAO ships with.

Each spec carries the parent policy (scope + name) so the seed loader can
get-or-create the policy row before inserting the rule.

Severity values match the realtime AlertRaised severity enum so rule -> alert
routing carries the same value the WebSocket client already understands.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuleSpec:
    rule_key: str
    scope: str  # one of POLICY_SCOPES
    policy_name: str
    expression: dict[str, Any]
    threshold: float | None
    severity: str  # one of POLICY_RULE_SEVERITIES
    description: str


DEFAULT_RULES: tuple[RuleSpec, ...] = (
    RuleSpec(
        rule_key="tea.compulsory_attendance.90_percent",
        scope="tea",
        policy_name="TEC §25.092 compulsory attendance",
        expression={"op": "lt", "field": "attendance_percent", "value": 90},
        threshold=90,
        severity="high",
        description="Student is on track to fall below the 90% attendance floor.",
    ),
    RuleSpec(
        rule_key="tea.truancy.unexcused_absences",
        scope="tea",
        policy_name="TEC §25.094 truancy",
        # Either trigger fires alone: 3 unexcused in any rolling 4-week
        # window, or 10 in any rolling 6-month window.
        expression={
            "op": "or",
            "args": [
                {"op": "gte", "field": "unexcused_absences_4_weeks", "value": 3},
                {"op": "gte", "field": "unexcused_absences_6_months", "value": 10},
            ],
        },
        threshold=3,
        severity="critical",
        description="Truancy threshold reached under TEC §25.094.",
    ),
    RuleSpec(
        rule_key="pfisd.18_day_max",
        scope="district",
        policy_name="PfISD attendance escalation",
        # PfISD policy is 18 absences max; we alert at 15 to give the team
        # a runway to intervene before the hard limit.
        expression={"op": "gte", "field": "absences", "value": 15},
        threshold=15,
        severity="medium",
        description="Approaching PfISD 18-day absence limit; intervention window open.",
    ),
    RuleSpec(
        rule_key="restroom.duration_exceeded",
        scope="school",
        policy_name="Hall pass duration limits",
        # Wired to Phase 6's 15-min on-duty admin alert. Tighten or relax
        # by editing this value, not hardcoding elsewhere.
        expression={"op": "gt", "field": "minutes_elapsed", "value": 15},
        threshold=15,
        severity="high",
        description="Student has been on a restroom hall pass beyond the duration limit.",
    ),
)


__all__ = ["DEFAULT_RULES", "RuleSpec"]
