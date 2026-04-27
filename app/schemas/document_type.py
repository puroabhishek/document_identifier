from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DocumentTypeCreate(BaseModel):
    name: str
    class_label: str
    subject_type: Literal["business", "individual"]
    description: str | None = None
    issuing_agency: str | None = None


class DocumentTypeUpdate(BaseModel):
    name: str | None = None
    class_label: str | None = None
    subject_type: Literal["business", "individual"] | None = None
    description: str | None = None
    issuing_agency: str | None = None
    is_active: bool | None = None


class DocumentTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    class_label: str
    subject_type: str
    description: str | None
    issuing_agency: str | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
