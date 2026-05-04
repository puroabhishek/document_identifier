import io
from unittest.mock import MagicMock

import openpyxl
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.classification.engine import ClassificationEngine
from app.config import Settings
from app.core.protocols import ServiceResult
from app.models.document_type import DocumentType

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _make_xlsx_bytes(sheet_name: str) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(["Vendor", "accounts payable", "supplier", "creditor", "AP ageing", "0-30 days"])
    ws.append(["Supplier A", 1000, 500, 200, "payable ageing", 100])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_settings() -> Settings:
    return Settings(database_url="sqlite+aiosqlite:///:memory:")


def _make_service_mock(class_label: str, confidence: float):
    mock = MagicMock()
    mock.classify.return_value = ServiceResult(
        predicted_class=class_label, confidence=confidence, raw_response={}
    )
    return mock


@pytest_asyncio.fixture
async def seeded_db(db_session: AsyncSession) -> AsyncSession:
    db_session.add(DocumentType(
        name="Payable Ageing Report",
        class_label="payable_ageing_report",
        subject_type="business",
    ))
    db_session.add(DocumentType(
        name="Bank Statement",
        class_label="bank_statement",
        subject_type="business",
    ))
    await db_session.commit()
    return db_session


@pytest.mark.asyncio
async def test_xlsx_rule_based_path(seeded_db: AsyncSession):
    engine = ClassificationEngine(_make_settings(), _make_service_mock("", 0.0))
    content = _make_xlsx_bytes("Payable Ageing")
    result = await engine.classify(content, XLSX_MIME, "report.xlsx", seeded_db)
    assert result.classification_method == "rule_based"
    assert result.matched_type_name == "Payable Ageing Report"


@pytest.mark.asyncio
async def test_local_llm_path_for_pdf(seeded_db: AsyncSession):
    service = _make_service_mock("bank_statement", 0.92)
    engine = ClassificationEngine(_make_settings(), service)
    result = await engine.classify(b"%PDF fake", "application/pdf", "statement.pdf", seeded_db)
    assert result.classification_method == "local_llm"
    assert result.matched_type_name == "Bank Statement"
    assert result.confidence == 0.92


@pytest.mark.asyncio
async def test_unclassified_when_confidence_below_threshold(seeded_db: AsyncSession):
    settings = _make_settings()
    settings.confidence_threshold = 0.8
    service = _make_service_mock("bank_statement", 0.4)
    engine = ClassificationEngine(settings, service)
    result = await engine.classify(b"%PDF fake", "application/pdf", "doc.pdf", seeded_db)
    assert result.classification_method == "unclassified"
    assert result.matched_type_name is None


@pytest.mark.asyncio
async def test_unclassified_on_service_exception(seeded_db: AsyncSession):
    mock_service = MagicMock()
    mock_service.classify.side_effect = Exception("Ollama unavailable")
    engine = ClassificationEngine(_make_settings(), mock_service)
    result = await engine.classify(b"%PDF fake", "application/pdf", "doc.pdf", seeded_db)
    assert result.classification_method == "unclassified"
    assert result.error_message == "Ollama unavailable"


@pytest.mark.asyncio
async def test_subject_type_returned(seeded_db: AsyncSession):
    service = _make_service_mock("bank_statement", 0.95)
    engine = ClassificationEngine(_make_settings(), service)
    result = await engine.classify(b"%PDF fake", "application/pdf", "doc.pdf", seeded_db)
    assert result.subject_type == "business"
