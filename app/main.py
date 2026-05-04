from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import Settings, get_settings
from app.core.container import init_container
from app.db.base import create_tables, get_session_factory
from app.db.seed import run_seed
from app.exceptions import register_exception_handlers
from app.routers import classify, document_types, health, training


def _validate_ollama(settings: Settings) -> None:
    try:
        httpx.get(f"{settings.ollama_host}/api/tags", timeout=5.0).raise_for_status()
    except Exception as exc:
        raise RuntimeError(
            f"Ollama unreachable at {settings.ollama_host}. "
            f"Run: ollama serve && ollama pull {settings.ollama_model}. "
            f"Error: {exc}"
        ) from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await create_tables()
    await run_seed()

    container = init_container(settings)
    _validate_ollama(settings)

    try:
        factory = get_session_factory()
        async with factory() as session:
            await container.refresh_prompt_context(session)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Could not load prompt examples at startup: %s — "
            "examples load after first training document upload.", exc
        )

    yield


app = FastAPI(
    title="Document Identifier API",
    version="1.0.0",
    description=(
        "Classifies uploaded business and individual documents using a fully local pipeline. "
        "Supports 15 document types across business and individual/shareholder categories. "
        "All processing is in-process — no document data leaves the server (QCB data residency compliant)."
    ),
    lifespan=lifespan,
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(classify.router, prefix="/api/v1")
app.include_router(document_types.router, prefix="/api/v1")
app.include_router(training.router, prefix="/api/v1")
