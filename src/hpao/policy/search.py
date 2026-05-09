from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import PolicyChunk
from hpao.policy.embeddings import Embedder


async def search_policy_chunks(
    session: AsyncSession,
    *,
    query_embedding: list[float],
    limit: int = 5,
    policy_id: UUID | None = None,
) -> list[tuple[PolicyChunk, float]]:
    """Return chunks closest to the query embedding by cosine distance.

    Caller pre-computes the embedding so search is decoupled from the
    embedding service — useful for batch queries and for tests that want
    full control over the vector. Lower distance == more similar.
    """
    distance = PolicyChunk.embedding.cosine_distance(query_embedding).label("distance")
    stmt = (
        select(PolicyChunk, distance)
        .where(PolicyChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    if policy_id is not None:
        stmt = stmt.where(PolicyChunk.policy_id == policy_id)

    result = await session.execute(stmt)
    return [(chunk, float(dist)) for chunk, dist in result.all()]


async def search_policy(
    session: AsyncSession,
    embedder: Embedder,
    query: str,
    *,
    limit: int = 5,
    policy_id: UUID | None = None,
) -> list[tuple[PolicyChunk, float]]:
    """Convenience wrapper: embed the query, then run cosine search.

    Phase 8's `/v1/agent/policy-search` endpoint composes this directly.
    """
    [embedding] = await embedder.embed([query])
    return await search_policy_chunks(
        session, query_embedding=embedding, limit=limit, policy_id=policy_id
    )
