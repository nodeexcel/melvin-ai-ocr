import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_SYNC_URL", "sqlite:///test.db")
os.environ.setdefault("SECRET_KEY", "testsecretkey")
os.environ.setdefault("OPENAI_API_KEY", "test")

import app.database as _app_database  # noqa: E402
import app.routers.stream as _stream_router  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_engine = None
_session_factory = None


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    async with engine.connect() as conn:
        await conn.begin_nested()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


@pytest_asyncio.fixture
async def client(engine, db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Patch AsyncSessionLocal so _event_generator (which opens its own session via
    # _app_database.AsyncSessionLocal()) uses the SAME db_session — same connection,
    # same savepoint — instead of opening a separate connection that would invalidate
    # the fixture's savepoint on teardown.
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _test_session_factory():
        yield db_session

    original_session_local = _app_database.AsyncSessionLocal
    _app_database.AsyncSessionLocal = _test_session_factory

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    _app_database.AsyncSessionLocal = original_session_local
    app.dependency_overrides.clear()
