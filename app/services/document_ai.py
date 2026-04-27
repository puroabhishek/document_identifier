from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings


@dataclass
class DocAIResult:
    predicted_class: str
    confidence: float
    raw_response: dict[str, Any]


class DocumentAIService:
    def __init__(self, settings: "Settings") -> None:
        self._project = settings.google_cloud_project_id
        self._location = settings.document_ai_location
        self._processor_id = settings.document_ai_processor_id
        self._settings = settings
        self._client = None
        self._processor_name: str | None = None

    def _get_client(self):
        if self._client is None:
            from google.cloud import documentai  # noqa: PLC0415
            from google.api_core.client_options import ClientOptions  # noqa: PLC0415
            opts = ClientOptions(api_endpoint=f"{self._location}-documentai.googleapis.com")
            self._client = documentai.DocumentProcessorServiceClient(client_options=opts)
            self._processor_name = self._client.processor_path(
                self._project, self._location, self._processor_id
            )
        return self._client

    def classify(self, content: bytes, mime_type: str) -> DocAIResult:
        from google.cloud import documentai  # noqa: PLC0415

        client = self._get_client()
        raw_doc = documentai.RawDocument(content=content, mime_type=mime_type)
        request = documentai.ProcessRequest(name=self._processor_name, raw_document=raw_doc)
        response = client.process_document(request=request)

        best_class = "unknown"
        best_conf = 0.0
        raw: dict[str, Any] = {"entities": []}

        for entity in response.document.entities:
            raw["entities"].append({"type": entity.type_, "confidence": entity.confidence})
            if entity.confidence > best_conf:
                best_conf = entity.confidence
                best_class = entity.type_

        return DocAIResult(
            predicted_class=best_class,
            confidence=best_conf,
            raw_response=raw,
        )
