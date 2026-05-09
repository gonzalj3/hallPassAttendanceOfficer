import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import Policy, PolicyRule
from hpao.policy import DEFAULT_RULES, seed_default_rules

pytestmark = pytest.mark.integration


async def test_seed_inserts_every_default_rule(async_session: AsyncSession) -> None:
    rules = await seed_default_rules(async_session)

    expected_keys = {r.rule_key for r in DEFAULT_RULES}
    assert set(rules) == expected_keys

    persisted = (await async_session.execute(select(PolicyRule))).scalars().all()
    assert {r.rule_key for r in persisted} == expected_keys


async def test_seed_creates_one_policy_per_unique_scope_name(
    async_session: AsyncSession,
) -> None:
    await seed_default_rules(async_session)

    policies = (await async_session.execute(select(Policy))).scalars().all()
    expected = {(r.scope, r.policy_name) for r in DEFAULT_RULES}
    actual = {(p.scope, p.name) for p in policies}
    assert actual == expected


async def test_seed_is_idempotent(async_session: AsyncSession) -> None:
    first = await seed_default_rules(async_session)
    second = await seed_default_rules(async_session)

    # Same rule_key set, same primary keys (no duplicate rows inserted).
    assert set(first) == set(second)
    for key in first:
        assert first[key].id == second[key].id

    rule_count = len((await async_session.execute(select(PolicyRule))).scalars().all())
    assert rule_count == len(DEFAULT_RULES)


async def test_seed_preserves_manual_rule_edits(async_session: AsyncSession) -> None:
    """Re-running seed must not stomp a hand-tuned rule."""
    await seed_default_rules(async_session)

    target_key = "restroom.duration_exceeded"
    rule = (
        await async_session.execute(select(PolicyRule).where(PolicyRule.rule_key == target_key))
    ).scalar_one()
    rule.expression = {"op": "gt", "field": "minutes_elapsed", "value": 10}  # tightened
    rule.threshold = 10
    await async_session.flush()

    await seed_default_rules(async_session)

    refreshed = (
        await async_session.execute(select(PolicyRule).where(PolicyRule.rule_key == target_key))
    ).scalar_one()
    assert refreshed.expression["value"] == 10
    assert refreshed.threshold == 10
