from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_db
from app.exceptions import DocumentTypeNotFoundError, TrainingDocumentNotFoundError
from app.models.document_type import DocumentType
from app.models.training_document import TrainingDocument
from app.schemas.training import TrainingDocumentRead, TrainResponse, TrainingStatusResponse

router = APIRouter(prefix="/training", tags=["training"])


def _gcs_client(settings: Settings):
    from google.cloud import storage
    return storage.Client(project=settings.google_cloud_project_id)


def _doc_ai_client(settings: Settings):
    from google.cloud import documentai
    from google.api_core.client_options import ClientOptions
    opts = ClientOptions(api_endpoint=f"{settings.document_ai_location}-documentai.googleapis.com")
    return documentai.DocumentProcessorServiceClient(client_options=opts)


@router.post("/documents", response_model=TrainingDocumentRead, status_code=201)
async def upload_training_document(
    document_type_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TrainingDocument:
    dt = await db.get(DocumentType, document_type_id)
    if dt is None:
        raise DocumentTypeNotFoundError(f"Document type {document_type_id} not found.")

    content = await file.read()
    gcs_path = f"training/{dt.class_label}/{file.filename}"
    gcs_uri = f"gs://{settings.gcs_training_bucket}/{gcs_path}"

    client = _gcs_client(settings)
    bucket = client.bucket(settings.gcs_training_bucket)
    blob = bucket.blob(gcs_path)
    blob.upload_from_string(content, content_type=file.content_type or "application/octet-stream")

    td = TrainingDocument(
        document_type_id=document_type_id,
        filename=file.filename or "unknown",
        gcs_uri=gcs_uri,
        file_size_bytes=len(content),
    )
    db.add(td)
    await db.commit()
    await db.refresh(td)
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
    settings: Settings = Depends(get_settings),
) -> Response:
    td = await db.get(TrainingDocument, training_doc_id)
    if td is None:
        raise TrainingDocumentNotFoundError(f"Training document {training_doc_id} not found.")

    try:
        client = _gcs_client(settings)
        bucket = client.bucket(settings.gcs_training_bucket)
        gcs_path = td.gcs_uri.replace(f"gs://{settings.gcs_training_bucket}/", "")
        bucket.blob(gcs_path).delete()
    except Exception:
        pass

    await db.delete(td)
    await db.commit()
    return Response(status_code=204)


@router.post("/train", response_model=TrainResponse)
async def trigger_training(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TrainResponse:
    result = await db.execute(select(TrainingDocument))
    training_docs = result.scalars().all()
    if not training_docs:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="No training documents uploaded yet.")

    result_dt = await db.execute(select(DocumentType).where(DocumentType.is_active == True))  # noqa: E712
    active_types = result_dt.scalars().all()
    label_map: dict[int, str] = {dt.id: dt.class_label for dt in active_types}

    from google.cloud import documentai
    from google.api_core.client_options import ClientOptions

    opts = ClientOptions(api_endpoint=f"{settings.document_ai_location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    processor_name = client.processor_path(
        settings.google_cloud_project_id, settings.document_ai_location, settings.document_ai_processor_id
    )

    labeled_docs = []
    for td in training_docs:
        class_label = label_map.get(td.document_type_id, "unknown")
        labeled_docs.append(
            documentai.LabeledDocument(
                gcs_document=documentai.GcsDocument(gcs_uri=td.gcs_uri, mime_type="application/pdf"),
                annotator_id=class_label,
            )
        )

    train_request = documentai.TrainProcessorVersionRequest(
        parent=processor_name,
        processor_version=documentai.ProcessorVersion(
            display_name="auto-trained-version"
        ),
        document_schema=documentai.DocumentSchema(
            entity_types=[
                documentai.DocumentSchema.EntityType(
                    name=class_label,
                    base_types=["object"],
                )
                for class_label in label_map.values()
            ]
        ),
    )

    operation = client.train_processor_version(request=train_request)
    op_name = operation.operation.name

    return TrainResponse(
        operation_name=op_name,
        message="Training started. Poll /api/v1/training/status?operation_name=... to check progress.",
    )


@router.get("/status", response_model=TrainingStatusResponse)
async def training_status(
    operation_name: str = Query(...),
    settings: Settings = Depends(get_settings),
) -> TrainingStatusResponse:
    from google.longrunning import operations_pb2
    from google.cloud import documentai
    from google.api_core.client_options import ClientOptions

    opts = ClientOptions(api_endpoint=f"{settings.document_ai_location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    op = client._transport._operations_client.get_operation(
        operations_pb2.GetOperationRequest(name=operation_name)
    )
    error_msg = op.error.message if op.error.code else None
    return TrainingStatusResponse(
        operation_name=operation_name,
        done=op.done,
        state="done" if op.done else "running",
        error=error_msg,
    )
