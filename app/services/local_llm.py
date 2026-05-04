from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import httpx

from app.core.protocols import ServiceResult

if TYPE_CHECKING:
    from app.config import Settings
    from app.parsers.docling_parser import DoclingParser
    from app.services.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class LocalLLMService:
    """Classifies documents using Docling (text extraction) + Qwen2.5 via Ollama.

    All processing is in-process on this server.
    No document bytes or extracted text leave the host.
    """

    def __init__(
        self,
        settings: "Settings",
        extractor: "DoclingParser",
        prompt_builder: "PromptBuilder",
    ) -> None:
        self._settings = settings
        self._extractor = extractor
        self._prompt_builder = prompt_builder

    def classify(self, content: bytes, mime_type: str) -> ServiceResult:
        text = self._extractor.parse(content)
        prompt = self._prompt_builder.build_classify_prompt(text)
        raw = self._call_ollama(prompt)
        predicted_class, confidence = self._parse_response(raw)
        return ServiceResult(
            predicted_class=predicted_class,
            confidence=confidence,
            raw_response={"llm_output": raw, "text_preview": text[:300]},
        )

    def _call_ollama(self, prompt: str) -> str:
        url = f"{self._settings.ollama_host}/api/generate"
        payload = {
            "model": self._settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0},
        }
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
        return resp.json()["response"]

    def _parse_response(self, raw: str) -> tuple[str, float]:
        try:
            data = json.loads(raw)
            label = str(data.get("class_label", "unknown"))
            confidence = float(data.get("confidence", 0.0))
            return label, confidence
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            logger.warning("Failed to parse Ollama response: %.200s", raw)
            return "unknown", 0.0
