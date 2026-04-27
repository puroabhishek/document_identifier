from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.classification.engine import ClassificationEngine
from app.config import Settings, get_settings
from app.db.session import get_db
from app.exceptions import FileTooLargeError, UnsupportedFileTypeError
from app.models.classification_log import ClassificationLog
from app.schemas.classification import ClassifyResponse
from app.services.document_ai import DocumentAIService

router = APIRouter(prefix="/documents", tags=["classify"])

_engine_cache: ClassificationEngine | None = None


def _get_engine(settings: Settings) -> ClassificationEngine:
    global _engine_cache
    if _engine_cache is None:
        doc_ai = DocumentAIService(settings)
        _engine_cache = ClassificationEngine(settings, doc_ai)
    return _engine_cache


@router.post("/classify", response_model=ClassifyResponse)
async def classify_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ClassifyResponse:
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()

    if ext not in settings.allowed_extensions:
        raise UnsupportedFileTypeError(
            f"Extension '{ext}' not supported. Allowed: {settings.allowed_extensions}"
        )

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise FileTooLargeError(
            f"File exceeds maximum size of {settings.max_upload_bytes // (1024 * 1024)} MB."
        )

    engine = _get_engine(settings)
    result = await engine.classify(
        content=content,
        content_type=file.content_type or "application/octet-stream",
        filename=filename,
        db=db,
    )

    log = ClassificationLog(
        filename=filename,
        file_content_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(content),
        classification_method=result.classification_method,
        confidence=result.confidence,
        matched_type_id=result.matched_type_id,
        matched_type_name=result.matched_type_name,
        subject_type=result.subject_type,
        doc_ai_raw_response=result.doc_ai_raw_response,
        error_message=result.error_message,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    return ClassifyResponse(
        document_type=result.matched_type_name,
        subject_type=result.subject_type,
        confidence=result.confidence,
        classification_method=result.classification_method,
        filename=filename,
        log_id=log.id,
    )
