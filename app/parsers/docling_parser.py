from __future__ import annotations

import io
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
    """Extracts plain text from PDF and DOCX files using pdfplumber (PDFs)
    and python-docx (DOCX). Falls back to empty string on any error.

    No ML models required — works on Intel Mac without PyTorch >= 2.4.
    """

    @staticmethod
    def _detect_suffix(content: bytes) -> str:
        if content[:4] == b"%PDF":
            return ".pdf"
        if content[:2] in (b"\xff\xd8", b"\xff\xe0", b"\xff\xe1"):
            return ".jpg"
        if content[:8] == b"\x89PNG\r\n\x1a\n":
            return ".png"
        if content[:4] == b"PK\x03\x04":
            return ".docx"
        return ".bin"

    def _extract_pdf(self, content: bytes) -> str:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages)

    def _extract_docx(self, content: bytes) -> str:
        import docx
        tmp = Path(tempfile.mktemp(suffix=".docx"))
        try:
            tmp.write_bytes(content)
            doc = docx.Document(str(tmp))
            return "\n".join(p.text for p in doc.paragraphs)
        finally:
            tmp.unlink(missing_ok=True)

    def parse(self, content: bytes) -> str:
        suffix = self._detect_suffix(content)
        if suffix == ".pdf":
            return self._normalise(self._extract_pdf(content))
        if suffix == ".docx":
            return self._normalise(self._extract_docx(content))
        return ""
