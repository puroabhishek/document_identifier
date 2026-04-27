import re
from abc import ABC, abstractmethod


class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: bytes) -> str: ...

    def _normalise(self, text: str) -> str:
        text = text.replace("\x00", "")
        return re.sub(r"\s+", " ", text).strip()
