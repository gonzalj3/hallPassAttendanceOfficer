from hpao.models import (
    EMBEDDING_DIM,
    POLICY_RULE_SEVERITIES,
    POLICY_SCOPES,
    Policy,
    PolicyChunk,
    PolicyRule,
)


class TestPolicyConstants:
    def test_scopes_match_three_authority_levels(self) -> None:
        assert POLICY_SCOPES == ("tea", "district", "school")

    def test_severities_match_alert_severity_enum(self) -> None:
        # Must match RealtimeEvent.Severity so an alert raised from a rule
        # carries a value the WS contract already knows.
        assert POLICY_RULE_SEVERITIES == ("low", "medium", "high", "critical")

    def test_embedding_dim_matches_text_embedding_3_small(self) -> None:
        assert EMBEDDING_DIM == 1536


class TestPolicy:
    def test_construction_with_required_fields(self) -> None:
        p = Policy(scope="tea", name="TEC §25.092 attendance")
        assert p.scope == "tea"
        assert p.name == "TEC §25.092 attendance"
        assert p.source_url is None
        assert p.version is None
        assert p.effective_date is None

    def test_repr_includes_scope_and_name(self) -> None:
        p = Policy(scope="district", name="PfISD attendance")
        rendered = repr(p)
        assert "district" in rendered
        assert "PfISD attendance" in rendered


class TestPolicyChunk:
    def test_construction_with_text_only(self) -> None:
        chunk = PolicyChunk(text="A student must attend at least 90% of days.")
        assert chunk.text.startswith("A student must attend")
        assert chunk.embedding is None

    def test_repr_truncates_long_text(self) -> None:
        long = "x" * 200
        chunk = PolicyChunk(text=long)
        assert "x" * 40 in repr(chunk)
        # repr should not contain the full 200-char text
        assert "x" * 200 not in repr(chunk)


class TestPolicyRule:
    def test_construction_with_jsonb_expression(self) -> None:
        rule = PolicyRule(
            rule_key="restroom.duration_exceeded",
            expression={"op": "gt", "field": "minutes_elapsed", "value": 15},
            severity="high",
        )
        assert rule.rule_key == "restroom.duration_exceeded"
        assert rule.expression["op"] == "gt"
        assert rule.severity == "high"
        assert rule.threshold is None

    def test_repr_includes_rule_key_and_severity(self) -> None:
        rule = PolicyRule(
            rule_key="tea.compulsory_attendance.90_percent",
            expression={},
            severity="medium",
        )
        rendered = repr(rule)
        assert "tea.compulsory_attendance.90_percent" in rendered
        assert "medium" in rendered
