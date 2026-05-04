from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.protocols import ClassificationServiceProtocol, ServiceResult
from app.parsers.factory import is_xlsx, get_xlsx_parser, get_mime_type
from app.classification.rule_based import score_xlsx

if TYPE_CHECKING:
    pass


@dataclass
class ClassificationResult:
    matched_type_name: str | None
    matched_type_id: int | None
    subject_type: str | None
    confidence: float
    classification_method: str  # "local_llm" | "rule_based" | "unclassified"
    llm_raw_response: dict[str, Any] | None = None
    error_message: str | None = None


class ClassificationEngine:
    def __init__(self, settings: Settings, service: ClassificationServiceProtocol) -> None:
        self._settings = settings
        self._service = service

    async def classify(
        self,
        content: bytes,
        content_type: str,
        filename: str,
        db: AsyncSession,
    ) -> ClassificationResult:
        from app.models.document_type import DocumentType

        result = await db.execute(
            select(DocumentType).where(DocumentType.is_active == True)  # noqa: E712
        )
        active_types = result.scalars().all()
        label_map: dict[str, DocumentType] = {dt.class_label: dt for dt in active_types}

        if is_xlsx(content_type, filename):
            return self._classify_xlsx(content, label_map)

        return self._classify_via_service(content, content_type, filename, label_map)

    def _classify_xlsx(
        self, content: bytes, label_map: dict
    ) -> ClassificationResult:
        try:
            text = get_xlsx_parser().parse(content)
        except Exception as exc:
            return ClassificationResult(
                matched_type_name=None,
                matched_type_id=None,
                subject_type=None,
                confidence=0.0,
                classification_method="unclassified",
                error_message=str(exc),
            )

        scores = score_xlsx(text)
        if scores and scores[0].score >= self._settings.xlsx_rule_threshold:
            best = scores[0]
            dt = label_map.get(best.class_label)
            return ClassificationResult(
                matched_type_name=dt.name if dt else best.class_label,
                matched_type_id=dt.id if dt else None,
                subject_type=dt.subject_type if dt else None,
                confidence=round(best.score, 4),
                classification_method="rule_based",
            )

        return ClassificationResult(
            matched_type_name=None,
            matched_type_id=None,
            subject_type=None,
            confidence=0.0,
            classification_method="unclassified",
        )

    def _classify_via_service(
        self,
        content: bytes,
        content_type: str,
        filename: str,
        label_map: dict,
    ) -> ClassificationResult:
        mime = get_mime_type(content_type, filename)
        try:
            result: ServiceResult = self._service.classify(content, mime)
        except Exception as exc:
            return ClassificationResult(
                matched_type_name=None,
                matched_type_id=None,
                subject_type=None,
                confidence=0.0,
                classification_method="unclassified",
                error_message=str(exc),
            )

        dt = label_map.get(result.predicted_class)
        if dt and result.confidence >= self._settings.confidence_threshold:
            return ClassificationResult(
                matched_type_name=dt.name,
                matched_type_id=dt.id,
                subject_type=dt.subject_type,
                confidence=round(result.confidence, 4),
                classification_method="local_llm",
                llm_raw_response=result.raw_response,
            )

        return ClassificationResult(
            matched_type_name=None,
            matched_type_id=None,
            subject_type=None,
            confidence=round(result.confidence, 4),
            classification_method="unclassified",
            llm_raw_response=result.raw_response,
        )
