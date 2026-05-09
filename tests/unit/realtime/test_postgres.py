from hpao.realtime import asyncpg_dsn


class TestAsyncpgDsn:
    def test_strips_asyncpg_driver_suffix(self) -> None:
        assert (
            asyncpg_dsn("postgresql+asyncpg://user:pass@host:5432/db")
            == "postgresql://user:pass@host:5432/db"
        )

    def test_passes_plain_postgres_url_through(self) -> None:
        assert (
            asyncpg_dsn("postgresql://user:pass@host:5432/db")
            == "postgresql://user:pass@host:5432/db"
        )

    def test_preserves_password_with_special_characters(self) -> None:
        # `render_as_string(hide_password=False)` keeps the password verbatim
        # so asyncpg.connect sees the same credentials SQLAlchemy did.
        assert "p%40ss" in asyncpg_dsn("postgresql+asyncpg://u:p%40ss@h/d")
