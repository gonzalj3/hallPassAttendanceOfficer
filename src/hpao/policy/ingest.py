from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import Policy, PolicyChunk
from hpao.policy.embeddings import Embedder

DEFAULT_CHUNK_CHARS = 1200


def chunk_text(text: str, *, max_chars: int = DEFAULT_CHUNK_CHARS) -> list[str]:
    """Split policy text on paragraph boundaries, falling back to char windows.

    Designed for embedding quality: paragraphs preserve semantic units, and
    only abnormally long paragraphs get hard-split. Preserves no surrounding
    whitespace; empty input yields ``[]``.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    for para in paragraphs:
        if len(para) <= max_chars:
            chunks.append(para)
        else:
            for start in range(0, len(para), max_chars):
                chunks.append(para[start : start + max_chars])
    return chunks


async def ingest_policy_text(
    session: AsyncSession,
    policy: Policy,
    text: str,
    embedder: Embedder,
    *,
    max_chars: int = DEFAULT_CHUNK_CHARS,
) -> list[PolicyChunk]:
    """Chunk, embed, and persist `text` as PolicyChunk rows for `policy`.

    Caller controls the transaction. Flushes so the chunks have IDs by the
    time we return, but does not commit — the same transaction wraps the
    batch and any data the caller persists alongside.
    """
    chunk_texts = chunk_text(text, max_chars=max_chars)
    if not chunk_texts:
        return []

    embeddings = await embedder.embed(chunk_texts)
    if len(embeddings) != len(chunk_texts):
        raise RuntimeError(
            f"embedder returned {len(embeddings)} vectors for {len(chunk_texts)} chunks"
        )

    chunks = [
        PolicyChunk(policy_id=policy.id, text=t, embedding=e)
        for t, e in zip(chunk_texts, embeddings, strict=True)
    ]
    session.add_all(chunks)
    await session.flush()
    return chunks
