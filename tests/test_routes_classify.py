import io
from unittest.mock import AsyncMock, MagicMock

import openpyxl
import pytest
from httpx import AsyncClient

from app.classification.engine import ClassificationEngine, ClassificationResult
from app.core.container import AppContainer
from app.models.document_type import DocumentType
from app.routers.classify import get_app_container


def _make_xlsx_bytes() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Payable Ageing"
    ws.append(["Vendor", "accounts payable", "supplier", "creditor", "AP ageing", "0-30 days"])
    ws.append(["Supplier A", 1000, 500, 200, "payable ageing", 100])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_mock_container(result: ClassificationResult) -> AppContainer:
    mock_engine = MagicMock(spec=ClassificationEngine)

    async def _classify(*args, **kwargs):
        return result

    mock_engine.classify.side_effect = _classify
    container = MagicMock(spec=AppContainer)
    container.engine = mock_engine
    return container


@pytest.mark.asyncio
async def test_classify_xlsx_payable(async_client: AsyncClient, db_session):
    dt = DocumentType(
        name="Payable Ageing Report",
        class_label="payable_ageing_report",
        subject_type="business",
    )
    db_session.add(dt)
    await db_session.commit()

    content = _make_xlsx_bytes()
    resp = await async_client.post(
        "/api/v1/documents/classify",
        files={"file": ("report.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["classification_method"] == "rule_based"
    assert data["filename"] == "report.xlsx"
    assert "log_id" in data


@pytest.mark.asyncio
async def test_classify_rejects_unsupported_extension(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/documents/classify",
        files={"file": ("malware.exe", b"binary", "application/octet-stream")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_classify_rejects_oversized_file(async_client: AsyncClient):
    big_content = b"x" * (21 * 1024 * 1024)
    resp = await async_client.post(
        "/api/v1/documents/classify",
        files={"file": ("big.pdf", big_content, "application/pdf")},
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_classify_response_has_subject_type(async_client: AsyncClient, db_session):
    from app.main import app

    dt = DocumentType(
        name="Payable Ageing Report 2",
        class_label="payable_ageing_report_2",
        subject_type="business",
    )
    db_session.add(dt)
    await db_session.commit()

    mock_container = _make_mock_container(
        ClassificationResult(
            matched_type_name="Payable Ageing Report 2",
            matched_type_id=dt.id,
            subject_type="business",
            confidence=0.9,
            classification_method="local_llm",
        )
    )

    app.dependency_overrides[get_app_container] = lambda: mock_container
    try:
        resp = await async_client.post(
            "/api/v1/documents/classify",
            files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["subject_type"] == "business"
        assert data["document_type"] == "Payable Ageing Report 2"
        assert data["classification_method"] == "local_llm"
    finally:
        app.dependency_overrides.pop(get_app_container, None)
