"""pytest config: override database engine with SQLite for all tests."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Build a single in-memory SQLite engine for the entire test session
_test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
_test_async_session = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _patch_db_engine():
    """Replace engine & session in database.db module with SQLite before any test runs."""
    import database.db as db_mod
    db_mod.engine = _test_engine
    db_mod.async_session = _test_async_session


@pytest.fixture(autouse=True)
async def _setup_tables():
    """Create all tables before each test, drop after."""
    from database.models import Base
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
