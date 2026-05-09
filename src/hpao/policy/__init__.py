"""Deterministic rule engine and policy RAG over the Phase 5a schema.

- `evaluator`: pure-Python evaluator for the JSONB rule DSL.
- `rules`: rule specifications (the 4 seed rules from CLAUDE.md live here).
- `seed`: idempotent loader that materializes the default rules into the DB.
- `embeddings`: Embedder protocol + OpenAI / stub implementations.
- `ingest`: chunk + embed policy doc text into PolicyChunk rows.
- `search`: cosine-similarity search over PolicyChunk embeddings (advisory
  RAG — must not override deterministic rule outcomes).
"""

from hpao.policy.embeddings import (
    DEFAULT_OPENAI_MODEL,
    Embedder,
    OpenAIEmbedder,
    StubEmbedder,
)
from hpao.policy.evaluator import RuleEvaluationError, evaluate
from hpao.policy.ingest import DEFAULT_CHUNK_CHARS, chunk_text, ingest_policy_text
from hpao.policy.rules import DEFAULT_RULES, RuleSpec
from hpao.policy.search import search_policy, search_policy_chunks
from hpao.policy.seed import seed_default_rules

__all__ = [
    "DEFAULT_CHUNK_CHARS",
    "DEFAULT_OPENAI_MODEL",
    "DEFAULT_RULES",
    "Embedder",
    "OpenAIEmbedder",
    "RuleEvaluationError",
    "RuleSpec",
    "StubEmbedder",
    "chunk_text",
    "evaluate",
    "ingest_policy_text",
    "search_policy",
    "search_policy_chunks",
    "seed_default_rules",
]
