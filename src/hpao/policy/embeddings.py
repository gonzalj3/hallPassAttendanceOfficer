from typing import Protocol, runtime_checkable

from openai import AsyncOpenAI

DEFAULT_OPENAI_MODEL = "text-embedding-3-small"


@runtime_checkable
class Embedder(Protocol):
    """Async vector embedder. Returns one 1536-dim vector per input text."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder:
    """Embedder backed by OpenAI's embeddings endpoint.

    Takes the AsyncOpenAI client as a dependency so callers can configure
    the API key, base URL, and timeouts once and inject it everywhere; tests
    pass a mock client.
    """

    def __init__(self, client: AsyncOpenAI, model: str = DEFAULT_OPENAI_MODEL) -> None:
        self._client = client
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.embeddings.create(input=texts, model=self._model)
        return [list(item.embedding) for item in response.data]


class StubEmbedder:
    """Deterministic embedder for tests.

    Maps a fixed table of text -> vector. Raises KeyError on unknown input
    so tests that depend on specific vectors fail loudly rather than
    silently producing garbage.
    """

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(self._vectors[t]) for t in texts]
