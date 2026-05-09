from collections.abc import Callable
from typing import Any


class RuleEvaluationError(ValueError):
    """Raised when a rule expression is malformed or its context is incomplete."""


_COMPARISONS: dict[str, Callable[[Any, Any], bool]] = {
    "gt": lambda a, b: bool(a > b),
    "gte": lambda a, b: bool(a >= b),
    "lt": lambda a, b: bool(a < b),
    "lte": lambda a, b: bool(a <= b),
    "eq": lambda a, b: bool(a == b),
    "ne": lambda a, b: bool(a != b),
}


def evaluate(expression: dict[str, Any], context: dict[str, Any]) -> bool:
    """Evaluate a JSONB rule expression against a context dict.

    DSL grammar (recursive):
      - Comparison: ``{"op": "gt"|"gte"|"lt"|"lte"|"eq"|"ne",
                       "field": <key>, "value": <literal>}``
      - Membership: ``{"op": "in", "field": <key>, "value": [<literal>, ...]}``
      - Boolean:    ``{"op": "and"|"or", "args": [<expr>, ...]}``
      - Negation:   ``{"op": "not", "expr": <expr>}``

    Missing context fields and malformed expressions raise
    ``RuleEvaluationError`` rather than evaluating to False — the caller
    must distinguish "rule did not trigger" from "rule could not evaluate".
    """
    if not isinstance(expression, dict):
        raise RuleEvaluationError(f"expression must be dict, got {type(expression).__name__}")

    op = expression.get("op")
    if not isinstance(op, str):
        raise RuleEvaluationError(f"missing or non-string 'op' in {expression!r}")

    if op in _COMPARISONS:
        field, value = _require(expression, "field"), _require(expression, "value")
        return _COMPARISONS[op](_lookup(context, field), value)

    if op == "in":
        field, value = _require(expression, "field"), _require(expression, "value")
        if not isinstance(value, list):
            raise RuleEvaluationError(f"'in' requires list 'value', got {type(value).__name__}")
        return _lookup(context, field) in value

    if op in {"and", "or"}:
        args = expression.get("args")
        if not isinstance(args, list) or not args:
            raise RuleEvaluationError(f"{op!r} requires non-empty 'args' list")
        if op == "and":
            return all(evaluate(a, context) for a in args)
        return any(evaluate(a, context) for a in args)

    if op == "not":
        if "expr" not in expression:
            raise RuleEvaluationError("'not' requires 'expr'")
        return not evaluate(expression["expr"], context)

    raise RuleEvaluationError(f"unknown op {op!r}")


def _require(expression: dict[str, Any], key: str) -> Any:
    if key not in expression:
        raise RuleEvaluationError(f"{expression.get('op')!r} requires {key!r}")
    return expression[key]


def _lookup(context: dict[str, Any], field: str) -> Any:
    if field not in context:
        raise RuleEvaluationError(f"context missing field {field!r}")
    return context[field]
