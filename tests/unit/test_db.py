from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from lizzie.db import Base, make_engine, make_session_factory


def test_base_metadata_has_naming_convention() -> None:
    convention = Base.metadata.naming_convention
    assert convention["pk"] == "pk_%(table_name)s"
    assert convention["fk"] == "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
    assert convention["ck"] == "ck_%(table_name)s_%(constraint_name)s"


def test_make_engine_returns_async_engine() -> None:
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    assert isinstance(engine, AsyncEngine)


def test_make_session_factory_returns_factory() -> None:
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    factory = make_session_factory(engine)
    assert isinstance(factory, async_sessionmaker)
