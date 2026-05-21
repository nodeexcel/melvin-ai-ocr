#!/usr/bin/env python3
"""Create the initial admin user. Run once after migrations.

Usage:
    cd app/backend
    python create_user.py <username> <password>
"""
import asyncio
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth import create_user
from app.config import settings


async def main():
    if len(sys.argv) != 3:
        print("Usage: python create_user.py <username> <password>")
        sys.exit(1)
    username, password = sys.argv[1], sys.argv[2]
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        user = await create_user(session, username, password)
        await session.commit()
        print(f"Created user: {user.username} (id={user.id})")
    await engine.dispose()


asyncio.run(main())
