from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.exceptions import DocumentTypeNotFoundError
from app.models.document_type import DocumentType
from app.schemas.document_type import DocumentTypeCreate, DocumentTypeRead, DocumentTypeUpdate

router = APIRouter(prefix="/document-types", tags=["document-types"])


@router.get("", response_model=list[DocumentTypeRead])
async def list_document_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentType]:
    stmt = select(DocumentType)
    if not include_inactive:
        stmt = stmt.where(DocumentType.is_active == True)  # noqa: E712
    stmt = stmt.offset(skip).limit(limit).order_by(DocumentType.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=DocumentTypeRead, status_code=201)
async def create_document_type(
    body: DocumentTypeCreate,
    db: AsyncSession = Depends(get_db),
) -> DocumentType:
    existing = await db.execute(
        select(DocumentType).where(DocumentType.class_label == body.class_label)
    )
    if existing.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=f"class_label '{body.class_label}' already exists.")

    dt = DocumentType(**body.model_dump())
    db.add(dt)
    await db.commit()
    await db.refresh(dt)
    return dt


@router.put("/{doc_type_id}", response_model=DocumentTypeRead)
async def update_document_type(
    doc_type_id: int,
    body: DocumentTypeUpdate,
    db: AsyncSession = Depends(get_db),
) -> DocumentType:
    dt = await db.get(DocumentType, doc_type_id)
    if dt is None:
        raise DocumentTypeNotFoundError(f"Document type {doc_type_id} not found.")

    updates = body.model_dump(exclude_unset=True)
    updates["version"] = dt.version + 1
    await db.execute(
        update(DocumentType).where(DocumentType.id == doc_type_id).values(**updates)
    )
    await db.commit()
    await db.refresh(dt)
    return dt


@router.delete("/{doc_type_id}", status_code=204, response_class=Response)
async def delete_document_type(
    doc_type_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    dt = await db.get(DocumentType, doc_type_id)
    if dt is None:
        raise DocumentTypeNotFoundError(f"Document type {doc_type_id} not found.")

    await db.execute(
        update(DocumentType)
        .where(DocumentType.id == doc_type_id)
        .values(is_active=False, version=dt.version + 1)
    )
    await db.commit()
    return Response(status_code=204)
