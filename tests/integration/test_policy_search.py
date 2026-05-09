from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import EMBEDDING_DIM, PolicyChunk
from hpao.policy import (
    StubEmbedder,
    ingest_policy_text,
    search_policy,
    search_policy_chunks,
)
from tests.factories import PolicyChunkFactory, PolicyFactory

pytestmark = pytest.mark.integration


def _basis(index: int) -> list[float]:
    """Unit basis vector with a single 1 at `index`. Cosine distance between
    two basis vectors at different indices is 1.0; same index is 0.0."""
    vec = [0.0] * EMBEDDING_DIM
    vec[index] = 1.0
    return vec


async def test_search_orders_by_cosine_similarity(async_session: AsyncSession) -> None:
    policy = PolicyFactory.build()
    async_session.add(policy)
    await async_session.flush()

    near_chunk = PolicyChunkFactory.build(policy_id=policy.id, text="closest", embedding=_basis(0))
    medium_chunk = PolicyChunkFactory.build(
        policy_id=policy.id,
        text="middle",
        embedding=[1 / 2**0.5, 1 / 2**0.5, *([0.0] * (EMBEDDING_DIM - 2))],
    )
    far_chunk = PolicyChunkFactory.build(policy_id=policy.id, text="farthest", embedding=_basis(1))
    async_session.add_all([near_chunk, medium_chunk, far_chunk])
    await async_session.flush()

    results = await search_policy_chunks(async_session, query_embedding=_basis(0), limit=3)

    assert [chunk.text for chunk, _ in results] == ["closest", "middle", "farthest"]
    distances = [d for _, d in results]
    assert distances[0] == pytest.approx(0.0, abs=1e-6)
    assert distances == sorted(distances)


async def test_search_excludes_chunks_without_embedding(async_session: AsyncSession) -> None:
    policy = PolicyFactory.build()
    async_session.add(policy)
    await async_session.flush()

    embedded = PolicyChunkFactory.build(policy_id=policy.id, text="has vec", embedding=_basis(0))
    raw = PolicyChunkFactory.build(policy_id=policy.id, text="no vec", embedding=None)
    async_session.add_all([embedded, raw])
    await async_session.flush()

    results = await search_policy_chunks(async_session, query_embedding=_basis(0), limit=10)
    assert [c.text for c, _ in results] == ["has vec"]


async def test_policy_id_filter_scopes_results(async_session: AsyncSession) -> None:
    policy_a = PolicyFactory.build(name="A")
    policy_b = PolicyFactory.build(name="B")
    async_session.add_all([policy_a, policy_b])
    await async_session.flush()

    chunk_a = PolicyChunkFactory.build(policy_id=policy_a.id, text="from A", embedding=_basis(0))
    chunk_b = PolicyChunkFactory.build(policy_id=policy_b.id, text="from B", embedding=_basis(0))
    async_session.add_all([chunk_a, chunk_b])
    await async_session.flush()

    a_only = await search_policy_chunks(
        async_session, query_embedding=_basis(0), policy_id=policy_a.id
    )
    assert [c.text for c, _ in a_only] == ["from A"]


async def test_limit_caps_result_count(async_session: AsyncSession) -> None:
    policy = PolicyFactory.build()
    async_session.add(policy)
    await async_session.flush()

    # All ten chunks point at the query vector, so distance is identical
    # and only the LIMIT bound determines result count.
    chunks = [
        PolicyChunkFactory.build(policy_id=policy.id, text=f"chunk-{i}", embedding=_basis(0))
        for i in range(10)
    ]
    async_session.add_all(chunks)
    await async_session.flush()

    results = await search_policy_chunks(async_session, query_embedding=_basis(0), limit=3)
    assert len(results) == 3


async def test_empty_corpus_returns_empty(async_session: AsyncSession) -> None:
    results = await search_policy_chunks(
        async_session, query_embedding=_basis(0), policy_id=uuid4()
    )
    assert results == []


async def test_ingest_then_search_roundtrip(async_session: AsyncSession) -> None:
    policy = PolicyFactory.build(name="Restroom rules")
    async_session.add(policy)
    await async_session.flush()

    text = (
        "Students may leave the classroom for the restroom with permission.\n\n"
        "Restroom passes shorter than fifteen minutes are routine.\n\n"
        "After fifteen minutes the on-duty admin is alerted."
    )
    embedder = StubEmbedder(
        {
            "Students may leave the classroom for the restroom with permission.": _basis(0),
            "Restroom passes shorter than fifteen minutes are routine.": _basis(1),
            "After fifteen minutes the on-duty admin is alerted.": _basis(2),
            "what happens after a long restroom pass": _basis(2),
        }
    )

    ingested = await ingest_policy_text(async_session, policy, text, embedder)
    assert len(ingested) == 3
    persisted = (
        await async_session.execute(
            PolicyChunk.__table__.select().where(PolicyChunk.policy_id == policy.id)
        )
    ).all()
    assert len(persisted) == 3

    results = await search_policy(
        async_session, embedder, "what happens after a long restroom pass", limit=1
    )
    assert results[0][0].text == "After fifteen minutes the on-duty admin is alerted."


async def test_ingest_empty_text_no_chunks(async_session: AsyncSession) -> None:
    policy = PolicyFactory.build()
    async_session.add(policy)
    await async_session.flush()

    embedder = StubEmbedder({})  # never called
    chunks = await ingest_policy_text(async_session, policy, "", embedder)
    assert chunks == []
