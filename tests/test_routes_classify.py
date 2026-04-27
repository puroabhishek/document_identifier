import io
from unittest.mock import MagicMock, patch

import openpyxl
import pytest
from httpx import AsyncClient

from app.classification.engine import ClassificationEngine, ClassificationResult
from app.models.document_type import DocumentType
from app.routers import classify as classify_module


def _make_xlsx_bytes() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Payable Ageing"
    ws.append(["Vendor", "accounts payable", "supplier", "creditor", "AP ageing", "0-30 days"])
    ws.append(["Supplier A", 1000, 500, 200, "payable ageing", 100])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _mock_engine(result: ClassificationResult) -> ClassificationEngine:
    mock = MagicMock(spec=ClassificationEngine)
    import asyncio

    async def _classify(*args, **kwargs):
        return result

    mock.classify.side_effect = _classify
    return mock


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
    dt = DocumentType(
        name="Payable Ageing Report 2",
        class_label="payable_ageing_report_2",
        subject_type="business",
    )
    db_session.add(dt)
    await db_session.commit()

    classify_module._engine_cache = _mock_engine(
        ClassificationResult(
            matched_type_name="Payable Ageing Report 2",
            matched_type_id=dt.id,
            subject_type="business",
            confidence=0.9,
            classification_method="document_ai",
        )
    )

    try:
        resp = await async_client.post(
            "/api/v1/documents/classify",
            files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["subject_type"] == "business"
        assert data["document_type"] == "Payable Ageing Report 2"
    finally:
        classify_module._engine_cache = None
