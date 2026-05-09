"""Deterministic rule engine over the policy schema from Phase 5a.

- `evaluator`: pure-Python evaluator for the JSONB rule DSL.
- `rules`: rule specifications (the 4 seed rules from CLAUDE.md live here).
- `seed`: idempotent loader that materializes the default rules into the DB.
"""

from hpao.policy.evaluator import RuleEvaluationError, evaluate
from hpao.policy.rules import DEFAULT_RULES, RuleSpec
from hpao.policy.seed import seed_default_rules

__all__ = [
    "DEFAULT_RULES",
    "RuleEvaluationError",
    "RuleSpec",
    "evaluate",
    "seed_default_rules",
]
