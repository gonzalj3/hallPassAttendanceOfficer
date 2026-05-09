from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from hpao.policy import OpenAIEmbedder, StubEmbedder
from hpao.policy.embeddings import DEFAULT_OPENAI_MODEL, Embedder


def _fake_response(vectors: list[list[float]]) -> Any:
    return SimpleNamespace(data=[SimpleNamespace(embedding=v) for v in vectors])


class TestOpenAIEmbedder:
    @pytest.mark.asyncio
    async def test_calls_embeddings_endpoint_with_model_and_inputs(self) -> None:
        client = SimpleNamespace(
            embeddings=SimpleNamespace(
                create=AsyncMock(return_value=_fake_response([[0.1, 0.2], [0.3, 0.4]]))
            )
        )

        embedder = OpenAIEmbedder(client, model=DEFAULT_OPENAI_MODEL)  # type: ignore[arg-type]
        out = await embedder.embed(["alpha", "beta"])

        assert out == [[0.1, 0.2], [0.3, 0.4]]
        client.embeddings.create.assert_awaited_once_with(
            input=["alpha", "beta"], model=DEFAULT_OPENAI_MODEL
        )

    @pytest.mark.asyncio
    async def test_empty_input_short_circuits_without_api_call(self) -> None:
        client = SimpleNamespace(embeddings=SimpleNamespace(create=AsyncMock()))
        embedder = OpenAIEmbedder(client)  # type: ignore[arg-type]

        assert await embedder.embed([]) == []
        client.embeddings.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_uses_custom_model_when_provided(self) -> None:
        client = SimpleNamespace(
            embeddings=SimpleNamespace(create=AsyncMock(return_value=_fake_response([[1.0]])))
        )
        embedder = OpenAIEmbedder(client, model="text-embedding-3-large")  # type: ignore[arg-type]

        await embedder.embed(["hi"])
        client.embeddings.create.assert_awaited_once_with(
            input=["hi"], model="text-embedding-3-large"
        )


class TestStubEmbedder:
    @pytest.mark.asyncio
    async def test_returns_mapped_vectors(self) -> None:
        embedder = StubEmbedder({"a": [1.0, 0.0], "b": [0.0, 1.0]})
        assert await embedder.embed(["a", "b", "a"]) == [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]

    @pytest.mark.asyncio
    async def test_unknown_text_raises_keyerror(self) -> None:
        embedder = StubEmbedder({"a": [1.0]})
        with pytest.raises(KeyError):
            await embedder.embed(["a", "missing"])

    def test_satisfies_protocol(self) -> None:
        assert isinstance(StubEmbedder({}), Embedder)
