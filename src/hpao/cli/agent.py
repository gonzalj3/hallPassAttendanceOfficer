"""Run a single prompt through the HPAO agent loop.

Usage:
    python -m hpao.cli.agent "How many days has student S00042 been absent?"

Reads the same env (DATABASE_URL, OPENAI_*, PARENT_COMMS_*) as
`hpao.cli.dispatcher`. Pipes the prompt to `Runner.run`, prints the
final output. Useful for sanity-checking the tool surface without
spinning up a chat UI.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from agents import Runner
from openai import AsyncOpenAI

from hpao.agent.context import HpaoContext
from hpao.agent.officer import make_officer
from hpao.config import get_settings
from hpao.db import make_engine, make_session_factory
from hpao.policy.embeddings import Embedder, OpenAIEmbedder, StubEmbedder

logger = logging.getLogger(__name__)


async def _run(prompt: str) -> None:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_maker = make_session_factory(engine)

    embedder: Embedder
    if settings.openai_api_key:
        embedder = OpenAIEmbedder(
            client=AsyncOpenAI(api_key=settings.openai_api_key),
            model=settings.openai_embedding_model,
        )
    else:
        # No API key -> empty stub. policy_query will return [] until the
        # operator wires OPENAI_API_KEY in.
        embedder = StubEmbedder({})

    officer = make_officer(model=settings.openai_model)

    try:
        async with session_maker() as db, db.begin():
            ctx = HpaoContext(
                db=db,
                embedder=embedder,
                parent_comms_url=settings.parent_comms_url,
                parent_comms_secret=settings.parent_comms_secret,
            )
            result = await Runner.run(officer, prompt, context=ctx)
        print(result.final_output)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="+", help="Prompt to send to the officer agent")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(_run(" ".join(args.prompt)))


if __name__ == "__main__":
    main()
