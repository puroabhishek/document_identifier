from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClassLabel:
    label: str
    name: str
    description: str
    examples: list[str] = field(default_factory=list)


class PromptBuilder:
    """Assembles few-shot classification prompts from stored ClassLabel definitions.

    No I/O, no settings dependency — pure in-memory state.
    set_class_labels() is called at startup and after every training change.
    """

    def __init__(self) -> None:
        self._labels: list[ClassLabel] = []

    def set_class_labels(self, labels: list[ClassLabel]) -> None:
        self._labels = labels

    def build_classify_prompt(self, document_text: str) -> str:
        types_section = self._build_types_section()
        return (
            "You are a document classification engine for a Qatar fintech company.\n"
            "Classify the given document into exactly ONE of the following document types.\n"
            'Respond with ONLY valid JSON: {"class_label": "<label>", "confidence": <0.0-1.0>}\n\n'
            f"VALID DOCUMENT TYPES:\n{types_section}\n\n"
            f"DOCUMENT TO CLASSIFY:\n---\n{document_text[:1500]}\n---\n\n"
            'Respond with JSON only. If the type cannot be determined, use {"class_label": "unknown", "confidence": 0.0}'
        )

    def _build_types_section(self) -> str:
        lines = []
        for cl in self._labels:
            hint = self._extract_arabic_hint(cl.description)
            suffix = f" ({hint})" if hint else ""
            lines.append(f"- {cl.label}: {cl.name}{suffix}")
        return "\n".join(lines)

    @staticmethod
    def _extract_arabic_hint(description: str) -> str:
        """Return the Arabic name from 'Also known as ...' if present."""
        if not description:
            return ""
        marker = "Also known as '"
        idx = description.find(marker)
        if idx == -1:
            return ""
        start = idx + len(marker)
        end = description.find("'", start)
        return description[start:end] if end != -1 else ""

    def _build_examples_section(self) -> str:
        if not any(cl.examples for cl in self._labels):
            return ""
        parts = ["FEW-SHOT EXAMPLES:\n"]
        for cl in self._labels:
            if cl.examples:
                parts.append(f"Example — {cl.label}:\n{cl.examples[0][:200]}\n-> {cl.label}\n")
        parts.append("\n")
        return "\n".join(parts)
