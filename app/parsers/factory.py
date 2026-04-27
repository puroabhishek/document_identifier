from pathlib import Path

from app.parsers.base import BaseParser
from app.parsers.xlsx_parser import XlsxParser

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

DOCUMENT_AI_MIMES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/tiff",
    "image/bmp",
    "image/webp",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def is_xlsx(content_type: str, filename: str) -> bool:
    return content_type == XLSX_MIME or Path(filename).suffix.lower() == ".xlsx"


def get_document_ai_mime(content_type: str, filename: str) -> str:
    if content_type in DOCUMENT_AI_MIMES:
        return content_type
    ext_map = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    ext = Path(filename).suffix.lower()
    return ext_map.get(ext, content_type)


def get_xlsx_parser() -> BaseParser:
    return XlsxParser()
