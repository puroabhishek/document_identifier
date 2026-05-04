from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.classification.engine import ClassificationEngine
    from app.parsers.docling_parser import DoclingParser
    from app.services.local_llm import LocalLLMService
    from app.services.prompt_builder import PromptBuilder


@dataclass
class AppContainer:
    engine: "ClassificationEngine"
    prompt_builder: "PromptBuilder"
    text_extractor: "DoclingParser"

    async def refresh_prompt_context(self, db: AsyncSession) -> None:
        """Reload few-shot examples from DB into PromptBuilder.
        Call at startup and after every training document add/delete/rebuild."""
        from app.models.document_type import DocumentType
        from app.models.training_document import TrainingDocument
        from app.services.prompt_builder import ClassLabel

        dt_result = await db.execute(
            select(DocumentType).where(DocumentType.is_active == True)  # noqa: E712
        )
        doc_types = dt_result.scalars().all()

        labels: list[ClassLabel] = []
        for dt in doc_types:
            td_result = await db.execute(
                select(TrainingDocument).where(
                    TrainingDocument.document_type_id == dt.id,
                    TrainingDocument.extracted_text.is_not(None),
                )
            )
            training_docs = td_result.scalars().all()
            labels.append(
                ClassLabel(
                    label=dt.class_label,
                    name=dt.name,
                    description=dt.description or "",
                    examples=[td.extracted_text for td in training_docs if td.extracted_text],
                )
            )

        self.prompt_builder.set_class_labels(labels)


_container: AppContainer | None = None


def get_container() -> AppContainer:
    assert _container is not None, "AppContainer not initialized — call init_container() in lifespan"
    return _container


def init_container(settings: object) -> AppContainer:
    global _container
    from app.parsers.docling_parser import DoclingParser
    from app.services.local_llm import LocalLLMService
    from app.services.prompt_builder import PromptBuilder
    from app.classification.engine import ClassificationEngine

    extractor = DoclingParser()
    prompt_builder = PromptBuilder()
    service = LocalLLMService(settings=settings, extractor=extractor, prompt_builder=prompt_builder)
    engine = ClassificationEngine(settings=settings, service=service)
    _container = AppContainer(engine=engine, prompt_builder=prompt_builder, text_extractor=extractor)
    return _container
