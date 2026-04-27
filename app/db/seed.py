from __future__ import annotations

import os

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session_factory
from app.models.document_type import DocumentType


def _load_seed_data() -> list[dict]:
    seed_file = os.path.join(
        os.path.dirname(__file__), "..", "..", "prompts", "document_types", "seed_data.yaml"
    )
    seed_file = os.path.normpath(seed_file)
    with open(seed_file, "r") as f:
        data = yaml.safe_load(f)
    return data["document_types"]


async def run_seed() -> None:
    seed_data = _load_seed_data()
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            for entry in seed_data:
                existing = await session.execute(
                    select(DocumentType).where(DocumentType.class_label == entry["class_label"])
                )
                if existing.scalar_one_or_none() is None:
                    session.add(DocumentType(**entry))
