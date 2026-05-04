from pydantic import BaseModel


class ClassifyResponse(BaseModel):
    document_type: str | None
    subject_type: str | None
    confidence: float
    classification_method: str  # "local_llm" | "rule_based" | "unclassified"
    filename: str
    log_id: int
    extracted_fields: dict | None = None


class HealthResponse(BaseModel):
    status: str
    db: str
    version: str = "1.0.0"
