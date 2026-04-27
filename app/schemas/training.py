from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrainingDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_type_id: int
    filename: str
    gcs_uri: str
    file_size_bytes: int | None
    uploaded_at: datetime


class TrainResponse(BaseModel):
    operation_name: str
    message: str


class TrainingStatusResponse(BaseModel):
    operation_name: str
    done: bool
    state: str | None = None
    error: str | None = None
