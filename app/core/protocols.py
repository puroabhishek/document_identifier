from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ServiceResult:
    predicted_class: str
    confidence: float
    raw_response: dict[str, Any]
    extracted_fields: dict[str, Any] | None = None


@runtime_checkable
class ClassificationServiceProtocol(Protocol):
    def classify(self, content: bytes, mime_type: str) -> ServiceResult: ...
