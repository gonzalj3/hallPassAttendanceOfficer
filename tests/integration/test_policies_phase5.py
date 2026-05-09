from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import EMBEDDING_DIM, Policy, PolicyChunk, PolicyRule
from tests.factories import PolicyChunkFactory, PolicyFactory, PolicyRuleFactory

pytestmark = pytest.mark.integration


async def test_policy_roundtrip(async_session: AsyncSession) -> None:
    policy = PolicyFactory.build(
        scope="tea",
        name="TEC §25.092 compulsory attendance",
        source_url="https://statutes.capitol.texas.gov/Docs/ED/htm/ED.25.htm",
        version="2025",
        effective_date=date(2025, 8, 1),
    )
    async_session.add(policy)
    await async_session.flush()

    fetched = (
        await async_session.execute(select(Policy).where(Policy.id == policy.id))
    ).scalar_one()
    assert fetched.scope == "tea"
    assert fetched.version == "2025"
    assert fetched.created_at is not None


async def test_invalid_scope_rejected(async_session: AsyncSession) -> None:
    policy = PolicyFactory.build(scope="federal")  # not in POLICY_SCOPES
    async_session.add(policy)
    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_chunks_persisted_with_embedding(async_session: AsyncSession) -> None:
    policy = PolicyFactory.build()
    async_session.add(policy)
    await async_session.flush()

    embedding = [0.0] * EMBEDDING_DIM
    embedding[0] = 1.0
    chunk = PolicyChunkFactory.build(
        policy_id=policy.id,
        text="Compulsory attendance: at least 90% of days offered.",
        embedding=embedding,
    )
    async_session.add(chunk)
    await async_session.flush()

    fetched = (
        await async_session.execute(select(PolicyChunk).where(PolicyChunk.id == chunk.id))
    ).scalar_one()
    assert fetched.text.startswith("Compulsory attendance")
    assert fetched.embedding is not None
    assert len(fetched.embedding) == EMBEDDING_DIM
    assert fetched.embedding[0] == pytest.approx(1.0)


async def test_chunk_without_embedding_allowed(async_session: AsyncSession) -> None:
    policy = PolicyFactory.build()
    async_session.add(policy)
    await async_session.flush()

    chunk = PolicyChunkFactory.build(policy_id=policy.id, embedding=None)
    async_session.add(chunk)
    await async_session.flush()  # must not raise


async def test_rule_persisted_with_jsonb_expression(async_session: AsyncSession) -> None:
    policy = PolicyFactory.build()
    async_session.add(policy)
    await async_session.flush()

    rule = PolicyRuleFactory.build(
        policy_id=policy.id,
        rule_key="restroom.duration_exceeded",
        expression={"op": "gt", "field": "minutes_elapsed", "value": 15},
        threshold=15,
        severity="high",
    )
    async_session.add(rule)
    await async_session.flush()

    fetched = (
        await async_session.execute(select(PolicyRule).where(PolicyRule.id == rule.id))
    ).scalar_one()
    assert fetched.expression == {"op": "gt", "field": "minutes_elapsed", "value": 15}
    assert fetched.severity == "high"


async def test_rule_key_globally_unique(async_session: AsyncSession) -> None:
    policy_a = PolicyFactory.build(name="A")
    policy_b = PolicyFactory.build(name="B")
    async_session.add_all([policy_a, policy_b])
    await async_session.flush()

    r1 = PolicyRuleFactory.build(policy_id=policy_a.id, rule_key="dup.rule")
    r2 = PolicyRuleFactory.build(policy_id=policy_b.id, rule_key="dup.rule")
    async_session.add_all([r1, r2])

    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_invalid_severity_rejected(async_session: AsyncSession) -> None:
    policy = PolicyFactory.build()
    async_session.add(policy)
    await async_session.flush()

    bad = PolicyRuleFactory.build(policy_id=policy.id, severity="extreme")
    async_session.add(bad)

    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_policy_with_chunks_and_rules_relationship(
    async_session: AsyncSession,
) -> None:
    policy = PolicyFactory.build(name="Restroom rules")
    async_session.add(policy)
    await async_session.flush()

    chunks = [
        PolicyChunkFactory.build(policy_id=policy.id, text=f"Rule chunk {i}") for i in range(2)
    ]
    rules = [
        PolicyRuleFactory.build(
            policy_id=policy.id, rule_key=f"restroom.rule.{i}", severity="medium"
        )
        for i in range(2)
    ]
    async_session.add_all([*chunks, *rules])
    await async_session.flush()

    refreshed = (
        await async_session.execute(select(Policy).where(Policy.id == policy.id))
    ).scalar_one()
    await async_session.refresh(refreshed, attribute_names=["chunks", "rules"])
    assert len(refreshed.chunks) == 2
    assert len(refreshed.rules) == 2
