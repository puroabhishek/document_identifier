from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./document_identifier.db"

    # Local LLM (Ollama)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b"
    local_training_dir: str = "data/training"

    # Classification thresholds
    confidence_threshold: float = 0.6
    xlsx_rule_threshold: float = 0.5

    # Upload constraints
    max_upload_bytes: int = 20 * 1024 * 1024
    debug: bool = False
    allowed_extensions: list[str] = [".pdf", ".jpg", ".jpeg", ".png", ".docx", ".xlsx"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
