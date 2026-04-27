import io
from unittest.mock import MagicMock, patch

import openpyxl
import pytest
import pytest_asyncio
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.classification.engine import ClassificationEngine
from app.config import Settings
from app.models.document_type import DocumentType
from app.services.document_ai import DocAIResult, DocumentAIService

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
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        google_cloud_project_id="proj",
        document_ai_processor_id="proc",
        google_application_credentials="fake",
        gcs_training_bucket="bucket",
    )


def _make_doc_ai_mock(class_label: str, confidence: float) -> DocumentAIService:
    mock = MagicMock(spec=DocumentAIService)
    mock.classify.return_value = DocAIResult(
        predicted_class=class_label, confidence=confidence, raw_response={}
    )
    return mock


@pytest_asyncio.fixture
async def seeded_db(db_session: AsyncSession) -> AsyncSession:
    dt = DocumentType(
        name="Payable Ageing Report",
        class_label="payable_ageing_report",
        subject_type="business",
    )
    db_session.add(dt)
    dt2 = DocumentType(
        name="Bank Statement",
        class_label="bank_statement",
        subject_type="business",
    )
    db_session.add(dt2)
    await db_session.commit()
    return db_session


@pytest.mark.asyncio
async def test_xlsx_rule_based_path(seeded_db: AsyncSession):
    settings = _make_settings()
    engine = ClassificationEngine(settings, _make_doc_ai_mock("", 0.0))
    content = _make_xlsx_bytes("Payable Ageing")
    result = await engine.classify(content, XLSX_MIME, "report.xlsx", seeded_db)
    assert result.classification_method == "rule_based"
    assert result.matched_type_name == "Payable Ageing Report"


@pytest.mark.asyncio
async def test_doc_ai_path_for_pdf(seeded_db: AsyncSession):
    settings = _make_settings()
    doc_ai = _make_doc_ai_mock("bank_statement", 0.92)
    engine = ClassificationEngine(settings, doc_ai)
    result = await engine.classify(b"%PDF fake", "application/pdf", "statement.pdf", seeded_db)
    assert result.classification_method == "document_ai"
    assert result.matched_type_name == "Bank Statement"
    assert result.confidence == 0.92


@pytest.mark.asyncio
async def test_unclassified_when_confidence_below_threshold(seeded_db: AsyncSession):
    settings = _make_settings()
    settings.confidence_threshold = 0.8
    doc_ai = _make_doc_ai_mock("bank_statement", 0.4)
    engine = ClassificationEngine(settings, doc_ai)
    result = await engine.classify(b"%PDF fake", "application/pdf", "doc.pdf", seeded_db)
    assert result.classification_method == "unclassified"
    assert result.matched_type_name is None


@pytest.mark.asyncio
async def test_unclassified_on_doc_ai_exception(seeded_db: AsyncSession):
    settings = _make_settings()
    doc_ai = MagicMock(spec=DocumentAIService)
    doc_ai.classify.side_effect = Exception("GCP unavailable")
    engine = ClassificationEngine(settings, doc_ai)
    result = await engine.classify(b"%PDF fake", "application/pdf", "doc.pdf", seeded_db)
    assert result.classification_method == "unclassified"
    assert result.error_message == "GCP unavailable"


@pytest.mark.asyncio
async def test_subject_type_returned(seeded_db: AsyncSession):
    settings = _make_settings()
    doc_ai = _make_doc_ai_mock("bank_statement", 0.95)
    engine = ClassificationEngine(settings, doc_ai)
    result = await engine.classify(b"%PDF fake", "application/pdf", "doc.pdf", seeded_db)
    assert result.subject_type == "business"
