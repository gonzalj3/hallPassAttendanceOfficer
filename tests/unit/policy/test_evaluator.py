import pytest

from hpao.policy import DEFAULT_RULES, RuleEvaluationError, evaluate


class TestComparisons:
    @pytest.mark.parametrize(
        ("op", "lhs", "rhs", "expected"),
        [
            ("gt", 16, 15, True),
            ("gt", 15, 15, False),
            ("gte", 15, 15, True),
            ("gte", 14, 15, False),
            ("lt", 89, 90, True),
            ("lt", 90, 90, False),
            ("lte", 90, 90, True),
            ("lte", 91, 90, False),
            ("eq", "PRESENT", "PRESENT", True),
            ("eq", "PRESENT", "ABSENT", False),
            ("ne", "PRESENT", "ABSENT", True),
            ("ne", "PRESENT", "PRESENT", False),
        ],
    )
    def test_comparison_ops(self, op: str, lhs: object, rhs: object, expected: bool) -> None:
        assert evaluate({"op": op, "field": "x", "value": rhs}, {"x": lhs}) is expected


class TestMembership:
    def test_in_returns_true_when_field_in_list(self) -> None:
        expr = {"op": "in", "field": "status", "value": ["UNEXCUSED", "FLAGGED"]}
        assert evaluate(expr, {"status": "UNEXCUSED"}) is True

    def test_in_returns_false_when_field_absent_from_list(self) -> None:
        expr = {"op": "in", "field": "status", "value": ["UNEXCUSED", "FLAGGED"]}
        assert evaluate(expr, {"status": "PRESENT"}) is False

    def test_in_requires_list_value(self) -> None:
        expr = {"op": "in", "field": "x", "value": "not-a-list"}
        with pytest.raises(RuleEvaluationError, match="list"):
            evaluate(expr, {"x": "y"})


class TestBooleanComposition:
    def test_and_short_circuits(self) -> None:
        # second arg references missing field; if `and` short-circuits on
        # the false first arg, we never reach it.
        expr = {
            "op": "and",
            "args": [
                {"op": "lt", "field": "a", "value": 0},
                {"op": "gt", "field": "missing", "value": 0},
            ],
        }
        assert evaluate(expr, {"a": 5}) is False

    def test_or_short_circuits(self) -> None:
        expr = {
            "op": "or",
            "args": [
                {"op": "gt", "field": "a", "value": 0},
                {"op": "gt", "field": "missing", "value": 0},
            ],
        }
        assert evaluate(expr, {"a": 5}) is True

    def test_and_returns_true_when_all_true(self) -> None:
        expr = {
            "op": "and",
            "args": [
                {"op": "gte", "field": "a", "value": 1},
                {"op": "lte", "field": "a", "value": 10},
            ],
        }
        assert evaluate(expr, {"a": 5}) is True

    def test_or_with_no_args_rejected(self) -> None:
        with pytest.raises(RuleEvaluationError, match="non-empty"):
            evaluate({"op": "or", "args": []}, {})


class TestNegation:
    def test_not_inverts_result(self) -> None:
        expr = {"op": "not", "expr": {"op": "gt", "field": "a", "value": 0}}
        assert evaluate(expr, {"a": 5}) is False
        assert evaluate(expr, {"a": -1}) is True

    def test_not_requires_expr(self) -> None:
        with pytest.raises(RuleEvaluationError, match="expr"):
            evaluate({"op": "not"}, {})


class TestErrorPaths:
    def test_unknown_op_raises(self) -> None:
        with pytest.raises(RuleEvaluationError, match="unknown op"):
            evaluate({"op": "xor", "field": "x", "value": 1}, {"x": 1})

    def test_missing_op_raises(self) -> None:
        with pytest.raises(RuleEvaluationError, match="non-string 'op'"):
            evaluate({"field": "x", "value": 1}, {"x": 1})

    def test_non_dict_expression_raises(self) -> None:
        with pytest.raises(RuleEvaluationError, match="must be dict"):
            evaluate("not a dict", {})  # type: ignore[arg-type]

    def test_missing_context_field_raises(self) -> None:
        with pytest.raises(RuleEvaluationError, match="missing field"):
            evaluate({"op": "gt", "field": "x", "value": 1}, {})


class TestDefaultRules:
    """Each shipped rule must fire on its intended trigger and be quiet otherwise."""

    @pytest.fixture
    def by_key(self) -> dict[str, dict[str, object]]:
        return {r.rule_key: r.expression for r in DEFAULT_RULES}

    def test_compulsory_attendance_fires_below_90_percent(
        self, by_key: dict[str, dict[str, object]]
    ) -> None:
        expr = by_key["tea.compulsory_attendance.90_percent"]
        assert evaluate(expr, {"attendance_percent": 89.9}) is True
        assert evaluate(expr, {"attendance_percent": 90}) is False

    def test_truancy_fires_on_either_window(self, by_key: dict[str, dict[str, object]]) -> None:
        expr = by_key["tea.truancy.unexcused_absences"]
        # 3 in 4 weeks alone fires:
        assert (
            evaluate(
                expr,
                {"unexcused_absences_4_weeks": 3, "unexcused_absences_6_months": 5},
            )
            is True
        )
        # 10 in 6 months alone fires:
        assert (
            evaluate(
                expr,
                {"unexcused_absences_4_weeks": 1, "unexcused_absences_6_months": 10},
            )
            is True
        )
        # Neither threshold reached:
        assert (
            evaluate(
                expr,
                {"unexcused_absences_4_weeks": 2, "unexcused_absences_6_months": 9},
            )
            is False
        )

    def test_pfisd_18_day_alerts_at_15(self, by_key: dict[str, dict[str, object]]) -> None:
        expr = by_key["pfisd.18_day_max"]
        assert evaluate(expr, {"absences": 15}) is True
        assert evaluate(expr, {"absences": 14}) is False

    def test_restroom_duration_fires_above_15(self, by_key: dict[str, dict[str, object]]) -> None:
        expr = by_key["restroom.duration_exceeded"]
        assert evaluate(expr, {"minutes_elapsed": 16}) is True
        assert evaluate(expr, {"minutes_elapsed": 15}) is False
