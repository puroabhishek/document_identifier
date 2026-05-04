from __future__ import annotations

import tempfile
from pathlib import Path

from app.parsers.base import BaseParser

_EXT_MAP: dict[str, str] = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/tiff": ".tiff",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


class DoclingParser(BaseParser):
    """Converts PDF, image, and DOCX content to plain markdown text using Docling.

    One instance is shared across the application (held in AppContainer).
    The DocumentConverter is lazy-loaded on first use — cold start takes ~5 s
    while layout models are loaded; subsequent calls are fast.

    Fintech data-minimization guarantee: the temp file written for Docling is
    always deleted in a finally block, even if conversion raises an exception.
    Document bytes never linger on disk beyond the duration of a single call.
    """

    def __init__(self) -> None:
        self._converter = None

    def _get_converter(self):
        if self._converter is None:
            from docling.document_converter import DocumentConverter
            self._converter = DocumentConverter()
        return self._converter

    @staticmethod
    def _detect_suffix(content: bytes) -> str:
        # Detect common file types from magic bytes
        if content[:4] == b"%PDF":
            return ".pdf"
        if content[:2] in (b"\xff\xd8", b"\xff\xe0", b"\xff\xe1"):
            return ".jpg"
        if content[:8] == b"\x89PNG\r\n\x1a\n":
            return ".png"
        if content[:4] == b"PK\x03\x04":
            return ".docx"
        return ".bin"

    def parse(self, content: bytes) -> str:
        suffix = self._detect_suffix(content)
        tmp = Path(tempfile.mktemp(suffix=suffix))
        try:
            tmp.write_bytes(content)
            result = self._get_converter().convert(str(tmp))
            return self._normalise(result.document.export_to_markdown())
        finally:
            tmp.unlink(missing_ok=True)
