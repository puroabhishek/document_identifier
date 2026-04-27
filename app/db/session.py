from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        yield session
