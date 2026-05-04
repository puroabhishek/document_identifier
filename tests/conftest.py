import asyncio
import io
import os
import tempfile
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch

import openpyxl
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.classification.engine import ClassificationEngine
from app.config import get_settings
from app.core.container import AppContainer
from app.core.protocols import ServiceResult
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.routers.classify import get_app_container as classify_get_container
from app.routers.training import get_app_container as training_get_container
from app.services.prompt_builder import PromptBuilder


def _make_test_container() -> AppContainer:
    """A container with a mock LLM service — no Ollama or Docling required."""
    mock_service = MagicMock()
    mock_service.classify.return_value = ServiceResult(
        predicted_class="unknown", confidence=0.0, raw_response={}
    )
    mock_extractor = MagicMock()
    mock_extractor.parse.return_value = "extracted text"

    engine = ClassificationEngine(settings=get_settings(), service=mock_service)
    prompt_builder = PromptBuilder()
    return AppContainer(engine=engine, prompt_builder=prompt_builder, text_extractor=mock_extractor)


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

    test_container = _make_test_container()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[classify_get_container] = lambda: test_container
    app.dependency_overrides[training_get_container] = lambda: test_container

    with patch("app.main._validate_ollama"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_xlsx_payable() -> bytes:
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
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Receivable Ageing"
    ws.append(["Customer", "accounts receivable", "debtor", "AR ageing", "0-30 days", "31-60 days"])
    ws.append(["Debtor A", 2000, 800, 0, 200, 100])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
