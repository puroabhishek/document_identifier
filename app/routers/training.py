from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.container import AppContainer, get_container
from app.db.session import get_db
from app.exceptions import DocumentTypeNotFoundError, TrainingDocumentNotFoundError
from app.models.document_type import DocumentType
from app.models.training_document import TrainingDocument
from app.parsers.factory import get_mime_type
from app.schemas.training import TrainingDocumentRead, TrainResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training", tags=["training"])


def get_app_container() -> AppContainer:
    return get_container()


@router.post("/documents", response_model=TrainingDocumentRead, status_code=201)
async def upload_training_document(
    document_type_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    container: AppContainer = Depends(get_app_container),
) -> TrainingDocument:
    dt = await db.get(DocumentType, document_type_id)
    if dt is None:
        raise DocumentTypeNotFoundError(f"Document type {document_type_id} not found.")

    content = await file.read()
    filename = file.filename or "unknown"

    # Write file locally
    class_dir = Path(settings.local_training_dir) / dt.class_label
    class_dir.mkdir(parents=True, exist_ok=True)
    local_path = class_dir / filename
    local_path.write_bytes(content)

    # Extract text via Docling
    extracted_text: str | None = None
    try:
        mime = get_mime_type(file.content_type or "", filename)
        extracted_text = container.text_extractor.parse(content)
    except Exception as exc:
        logger.warning("Docling extraction failed for training doc '%s': %s", filename, exc)

    # Idempotent upsert — same (document_type_id, filename) updates rather than duplicates
    existing = await db.execute(
        select(TrainingDocument).where(
            TrainingDocument.document_type_id == document_type_id,
            TrainingDocument.filename == filename,
        )
    )
    td = existing.scalar_one_or_none()

    if td is not None:
        td.storage_uri = str(local_path)
        td.file_size_bytes = len(content)
        td.extracted_text = extracted_text
    else:
        td = TrainingDocument(
            document_type_id=document_type_id,
            filename=filename,
            storage_uri=str(local_path),
            file_size_bytes=len(content),
            extracted_text=extracted_text,
        )
        db.add(td)

    await db.commit()
    await db.refresh(td)

    await container.refresh_prompt_context(db)

    return td


@router.get("/documents", response_model=list[TrainingDocumentRead])
async def list_training_documents(
    document_type_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[TrainingDocument]:
    stmt = select(TrainingDocument)
    if document_type_id is not None:
        stmt = stmt.where(TrainingDocument.document_type_id == document_type_id)
    stmt = stmt.offset(skip).limit(limit).order_by(TrainingDocument.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.delete("/documents/{training_doc_id}", status_code=204, response_class=Response)
async def delete_training_document(
    training_doc_id: int,
    db: AsyncSession = Depends(get_db),
    container: AppContainer = Depends(get_app_container),
) -> Response:
    td = await db.get(TrainingDocument, training_doc_id)
    if td is None:
        raise TrainingDocumentNotFoundError(f"Training document {training_doc_id} not found.")

    Path(td.storage_uri).unlink(missing_ok=True)
    await db.delete(td)
    await db.commit()

    await container.refresh_prompt_context(db)
    return Response(status_code=204)


@router.post("/train", response_model=TrainResponse)
async def rebuild_training_cache(
    db: AsyncSession = Depends(get_db),
    container: AppContainer = Depends(get_app_container),
) -> TrainResponse:
    """Re-extract text for any training documents with missing extracted_text,
    then refresh the prompt builder. Synchronous — no polling required."""
    result = await db.execute(
        select(TrainingDocument).where(TrainingDocument.extracted_text.is_(None))
    )
    docs = result.scalars().all()

    rebuilt = 0
    for td in docs:
        path = Path(td.storage_uri)
        if not path.exists():
            logger.warning("Training file missing at %s, skipping", td.storage_uri)
            continue
        try:
            content = path.read_bytes()
            td.extracted_text = container.text_extractor.parse(content)
            await db.commit()
            rebuilt += 1
        except Exception as exc:
            logger.warning("Rebuild failed for '%s': %s", td.filename, exc)

    await container.refresh_prompt_context(db)

    return TrainResponse(
        message=f"Rebuilt extraction cache for {rebuilt} document(s). Prompt examples refreshed.",
        documents_rebuilt=rebuilt,
    )
