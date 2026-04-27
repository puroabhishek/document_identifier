import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_type import DocumentType


@pytest.mark.asyncio
async def test_list_returns_empty_when_no_types(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/document-types")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_document_type(async_client: AsyncClient):
    payload = {
        "name": "Test Doc",
        "class_label": "test_doc",
        "subject_type": "business",
        "description": "A test document",
        "issuing_agency": "Test Agency",
    }
    resp = await async_client.post("/api/v1/document-types", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["class_label"] == "test_doc"
    assert data["version"] == 1
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_duplicate_class_label_returns_409(async_client: AsyncClient):
    payload = {"name": "Doc A", "class_label": "unique_label_x", "subject_type": "business"}
    await async_client.post("/api/v1/document-types", json=payload)
    payload2 = {"name": "Doc B", "class_label": "unique_label_x", "subject_type": "individual"}
    resp = await async_client.post("/api/v1/document-types", json=payload2)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_increments_version(async_client: AsyncClient):
    payload = {"name": "Versioned Doc", "class_label": "versioned_doc", "subject_type": "business"}
    create_resp = await async_client.post("/api/v1/document-types", json=payload)
    doc_id = create_resp.json()["id"]

    update_resp = await async_client.put(
        f"/api/v1/document-types/{doc_id}", json={"description": "Updated description"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["version"] == 2


@pytest.mark.asyncio
async def test_soft_delete_sets_inactive(async_client: AsyncClient):
    payload = {"name": "Delete Me", "class_label": "delete_me_label", "subject_type": "individual"}
    create_resp = await async_client.post("/api/v1/document-types", json=payload)
    doc_id = create_resp.json()["id"]

    del_resp = await async_client.delete(f"/api/v1/document-types/{doc_id}")
    assert del_resp.status_code == 204

    list_resp = await async_client.get("/api/v1/document-types")
    labels = [d["class_label"] for d in list_resp.json()]
    assert "delete_me_label" not in labels


@pytest.mark.asyncio
async def test_include_inactive_shows_deleted(async_client: AsyncClient):
    payload = {"name": "Inactive Doc", "class_label": "inactive_doc_label", "subject_type": "business"}
    create_resp = await async_client.post("/api/v1/document-types", json=payload)
    doc_id = create_resp.json()["id"]
    await async_client.delete(f"/api/v1/document-types/{doc_id}")

    resp = await async_client.get("/api/v1/document-types?include_inactive=true")
    labels = [d["class_label"] for d in resp.json()]
    assert "inactive_doc_label" in labels


@pytest.mark.asyncio
async def test_update_nonexistent_returns_404(async_client: AsyncClient):
    resp = await async_client.put("/api/v1/document-types/99999", json={"description": "x"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
