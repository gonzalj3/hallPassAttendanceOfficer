"""Per-run context the OpenAI Agents SDK passes to each tool invocation.

The Agents SDK takes a generic `context` argument on `Runner.run()` and
forwards it to every `@function_tool`-decorated function via
`RunContextWrapper`. We use it to thread the DB session, parent-comms
config, and an Embedder through to the tools without globals.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from hpao.policy.embeddings import Embedder


@dataclass
class HpaoContext:
    db: AsyncSession
    embedder: Embedder
    parent_comms_url: str | None = None
    parent_comms_secret: str | None = None
