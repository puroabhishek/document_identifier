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
            lines.append(f"- {cl.label}: {cl.name}")
        return "\n".join(lines)

    def _build_examples_section(self) -> str:
        if not any(cl.examples for cl in self._labels):
            return ""
        parts = ["FEW-SHOT EXAMPLES (correct classifications):\n"]
        for cl in self._labels:
            for i, example in enumerate(cl.examples[:2]):
                parts.append(f"Example — {cl.label} ({i + 1}):\n{example[:800]}\n-> {cl.label}\n")
        parts.append("\n")
        return "\n".join(parts)
