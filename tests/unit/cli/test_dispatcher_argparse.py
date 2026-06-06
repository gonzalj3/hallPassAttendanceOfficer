"""The CLI runs DB I/O so the actual loop is integration-tested. This file
just confirms the argparse surface so a typo in the entry-point options
breaks the unit gate, not the demo at midnight."""

import argparse

import pytest

from lizzie.cli.dispatcher import main


def test_main_accepts_no_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default mode is the forever loop. Without DATABASE_URL set, it would
    crash inside asyncio.run -- so we patch asyncio.run to a no-op and
    confirm the parser accepted the args."""
    import asyncio

    called: list[object] = []
    monkeypatch.setattr(asyncio, "run", lambda coro: called.append(coro))
    main([])
    assert len(called) == 1


def test_main_accepts_once_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    called: list[object] = []
    monkeypatch.setattr(asyncio, "run", lambda coro: called.append(coro))
    main(["--once"])
    assert len(called) == 1


def test_main_accepts_interval_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    called: list[object] = []
    monkeypatch.setattr(asyncio, "run", lambda coro: called.append(coro))
    main(["--interval", "5"])
    assert len(called) == 1


def test_main_rejects_unknown_flag() -> None:
    with pytest.raises(SystemExit):
        main(["--bogus-flag"])


def test_main_invalid_interval_rejected() -> None:
    with pytest.raises((SystemExit, argparse.ArgumentError)):
        main(["--interval", "not-a-number"])
