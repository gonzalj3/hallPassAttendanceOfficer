"""Run the overdue-pass monitor loop.

Usage:
    python -m lizzie.cli.dispatcher              # forever loop
    python -m lizzie.cli.dispatcher --once       # single cycle, then exit
    python -m lizzie.cli.dispatcher --interval 5 # 5-second cycle for live demo

Reads DATABASE_URL and DISPATCHER_INTERVAL_SECONDS from env (or .env).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from lizzie.config import get_settings
from lizzie.db import make_engine, make_session_factory
from lizzie.services.dispatcher import (
    run_alert_dispatch_cycle,
    run_periodic_dispatcher,
)

logger = logging.getLogger(__name__)


async def _run_once() -> None:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_maker = make_session_factory(engine)
    try:
        async with session_maker() as db, db.begin():
            result = await run_alert_dispatch_cycle(db)
        print(f"new_alerts={len(result.new_alerts)}")
    finally:
        await engine.dispose()


async def _run_forever(interval: float | None) -> None:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_maker = make_session_factory(engine)
    try:
        await run_periodic_dispatcher(
            session_maker,
            interval_seconds=interval or settings.dispatcher_interval_seconds,
        )
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="run a single cycle and exit")
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help="override DISPATCHER_INTERVAL_SECONDS (forever mode only)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.once:
        asyncio.run(_run_once())
        return
    try:
        asyncio.run(_run_forever(args.interval))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
