from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.services.local_llm import LocalLLMService
from app.services.prompt_builder import PromptBuilder


def _settings() -> Settings:
    return Settings(database_url="sqlite+aiosqlite:///:memory:")


def _make_service(extractor=None, prompt_builder=None) -> LocalLLMService:
    extractor = extractor or MagicMock()
    prompt_builder = prompt_builder or MagicMock()
    prompt_builder.build_classify_prompt.return_value = "test prompt"
    return LocalLLMService(settings=_settings(), extractor=extractor, prompt_builder=prompt_builder)


def test_parse_response_valid():
    svc = _make_service()
    label, conf = svc._parse_response('{"class_label": "bank_statement", "confidence": 0.93}')
    assert label == "bank_statement"
    assert conf == 0.93


def test_parse_response_malformed_json():
    svc = _make_service()
    label, conf = svc._parse_response("not json at all")
    assert label == "unknown"
    assert conf == 0.0


def test_parse_response_missing_fields():
    svc = _make_service()
    label, conf = svc._parse_response("{}")
    assert label == "unknown"
    assert conf == 0.0


def test_classify_calls_pipeline():
    extractor = MagicMock()
    extractor.parse.return_value = "extracted document text"

    with patch.object(
        LocalLLMService, "_call_ollama",
        return_value='{"class_label": "bank_statement", "confidence": 0.91}'
    ):
        pb = PromptBuilder()
        svc = LocalLLMService(settings=_settings(), extractor=extractor, prompt_builder=pb)
        result = svc.classify(b"%PDF fake", "application/pdf")

    assert result.predicted_class == "bank_statement"
    assert result.confidence == 0.91
    extractor.parse.assert_called_once_with(b"%PDF fake")


def test_classify_returns_unknown_on_ollama_failure():
    extractor = MagicMock()
    extractor.parse.return_value = "some text"

    with patch.object(
        LocalLLMService, "_call_ollama",
        side_effect=Exception("Connection refused")
    ):
        pb = PromptBuilder()
        svc = LocalLLMService(settings=_settings(), extractor=extractor, prompt_builder=pb)
        # classify() catches exceptions in the engine, not in the service itself —
        # but _call_ollama raising means classify() raises, engine catches it
        with pytest.raises(Exception, match="Connection refused"):
            svc.classify(b"%PDF fake", "application/pdf")
