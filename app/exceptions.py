from fastapi import FastAPI
from fastapi.responses import JSONResponse


class UnsupportedFileTypeError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


class DocumentTypeNotFoundError(Exception):
    pass


class TrainingDocumentNotFoundError(Exception):
    pass


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UnsupportedFileTypeError)
    async def handle_unsupported(_req, exc: UnsupportedFileTypeError):
        return JSONResponse(status_code=415, content={"detail": str(exc)})

    @app.exception_handler(FileTooLargeError)
    async def handle_too_large(_req, exc: FileTooLargeError):
        return JSONResponse(status_code=413, content={"detail": str(exc)})

    @app.exception_handler(DocumentTypeNotFoundError)
    async def handle_not_found(_req, exc: DocumentTypeNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(TrainingDocumentNotFoundError)
    async def handle_training_not_found(_req, exc: TrainingDocumentNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})
