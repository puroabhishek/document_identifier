from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrainingDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_type_id: int
    filename: str
    storage_uri: str
    file_size_bytes: int | None
    extracted_text: str | None = None
    uploaded_at: datetime


class TrainResponse(BaseModel):
    message: str
    documents_rebuilt: int = 0
