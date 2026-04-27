from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.base import create_tables
from app.db.seed import run_seed
from app.exceptions import register_exception_handlers
from app.routers import classify, document_types, health, training


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await run_seed()
    yield


app = FastAPI(
    title="Document Identifier API",
    version="1.0.0",
    description=(
        "Classifies uploaded business and individual documents using Google Document AI. "
        "Supports 15 document types across business and individual/shareholder categories."
    ),
    lifespan=lifespan,
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(classify.router, prefix="/api/v1")
app.include_router(document_types.router, prefix="/api/v1")
app.include_router(training.router, prefix="/api/v1")
