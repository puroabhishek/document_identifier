from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
    )


def _make_session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = _make_session_factory(get_engine())
    return _session_factory


async def create_tables() -> None:
    from app.models import document_type, training_document, classification_log  # noqa: F401
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
