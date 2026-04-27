from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document_type import DocumentType


class ClassificationLog(Base):
    __tablename__ = "classification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    classification_method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "document_ai" | "rule_based" | "unclassified"
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    matched_type_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True
    )
    matched_type_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    subject_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    doc_ai_raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False, index=True
    )

    document_type: Mapped["DocumentType | None"] = relationship(back_populates="logs")
