from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./document_identifier.db"

    google_cloud_project_id: str = ""
    google_application_credentials: str = ""
    document_ai_location: str = "us"
    document_ai_processor_id: str = ""
    gcs_training_bucket: str = ""

    confidence_threshold: float = 0.6
    xlsx_rule_threshold: float = 0.5

    max_upload_bytes: int = 20 * 1024 * 1024
    debug: bool = False
    allowed_extensions: list[str] = [".pdf", ".jpg", ".jpeg", ".png", ".docx", ".xlsx"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
