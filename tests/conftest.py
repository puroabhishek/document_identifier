import asyncio
import os
import tempfile
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def test_engine():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_url = f"sqlite+aiosqlite:///{tmp.name}"
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    os.unlink(tmp.name)


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_xlsx_payable() -> bytes:
    import io
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Payable Ageing"
    ws.append(["Vendor", "accounts payable", "supplier", "creditor", "AP ageing", "0-30 days"])
    ws.append(["Supplier A", 1000, 500, 200, "payable ageing", 100])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture
def sample_xlsx_receivable() -> bytes:
    import io
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Receivable Ageing"
    ws.append(["Customer", "accounts receivable", "debtor", "AR ageing", "0-30 days", "31-60 days"])
    ws.append(["Debtor A", 2000, 800, 0, 200, 100])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
