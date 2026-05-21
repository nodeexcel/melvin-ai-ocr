import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.models import Base, User


def test_models_importable():
    from app.models import AnalysisResult, JobEvent, Project, User
    assert User.__tablename__ == "users"
    assert Project.__tablename__ == "projects"
    assert JobEvent.__tablename__ == "job_events"
    assert AnalysisResult.__tablename__ == "analysis_results"


@pytest.mark.asyncio
async def test_models_roundtrip():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            username="testuser",
            hashed_password="fakehash",
        )
        session.add(user)
        await session.commit()

    async with session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.username == "testuser"))
        fetched = result.scalar_one()
        assert fetched.username == "testuser"
        assert fetched.hashed_password == "fakehash"

    await engine.dispose()
