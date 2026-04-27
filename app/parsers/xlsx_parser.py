import io

import openpyxl

from app.parsers.base import BaseParser


class XlsxParser(BaseParser):
    def parse(self, content: bytes) -> str:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        parts: list[str] = []
        for sheet in wb.worksheets:
            parts.append(f"[Sheet: {sheet.title}]")
            for row in sheet.iter_rows(values_only=True):
                row_text = " | ".join(str(c) for c in row if c is not None)
                if row_text.strip():
                    parts.append(row_text)
        wb.close()
        return self._normalise("\n".join(parts))
