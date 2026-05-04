from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core import container as container_module
from app.core.container import AppContainer, init_container, get_container


def _settings() -> Settings:
    return Settings(database_url="sqlite+aiosqlite:///:memory:")


@pytest.fixture(autouse=True)
def reset_container():
    """Ensure container state is reset between tests."""
    original = container_module._container
    yield
    container_module._container = original


def test_init_container_creates_all_components():
    with patch("app.parsers.docling_parser.DoclingParser"):
        container = init_container(_settings())
    assert container.engine is not None
    assert container.prompt_builder is not None
    assert container.text_extractor is not None


def test_get_container_raises_before_init():
    container_module._container = None
    with pytest.raises(AssertionError):
        get_container()


def test_get_container_returns_same_instance():
    with patch("app.parsers.docling_parser.DoclingParser"):
        c1 = init_container(_settings())
    c2 = get_container()
    assert c1 is c2


@pytest.mark.asyncio
async def test_refresh_prompt_context_with_empty_db(db_session: AsyncSession):
    with patch("app.parsers.docling_parser.DoclingParser"):
        container = init_container(_settings())
    # No document types in DB — should set empty label list without error
    await container.refresh_prompt_context(db_session)
    assert container.prompt_builder._labels == []


@pytest.mark.asyncio
async def test_refresh_prompt_context_loads_doc_types(db_session: AsyncSession):
    from app.models.document_type import DocumentType

    db_session.add(DocumentType(
        name="Bank Statement", class_label="bank_statement", subject_type="business"
    ))
    await db_session.commit()

    with patch("app.parsers.docling_parser.DoclingParser"):
        container = init_container(_settings())
    await container.refresh_prompt_context(db_session)

    labels = container.prompt_builder._labels
    assert len(labels) == 1
    assert labels[0].label == "bank_statement"
    assert labels[0].name == "Bank Statement"
