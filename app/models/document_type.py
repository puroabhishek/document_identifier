from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.training_document import TrainingDocument
    from app.models.classification_log import ClassificationLog


class DocumentType(Base):
    __tablename__ = "document_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    class_label: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(
        Enum("business", "individual", name="subject_type_enum"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    issuing_agency: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    training_documents: Mapped[list["TrainingDocument"]] = relationship(
        back_populates="document_type", cascade="all, delete-orphan"
    )
    logs: Mapped[list["ClassificationLog"]] = relationship(back_populates="document_type")
