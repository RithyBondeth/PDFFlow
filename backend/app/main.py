from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import download, health, jobs, upload
from app.core.config import settings
from app.core.errors import PDFFlowError
from app.core.logging import configure_logging
from app.services.rate_limit import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings.ensure_directories()
    logger.info("api_started", extra={"environment": settings.environment})
    yield


app = FastAPI(
    title="PDFFlow API",
    version="0.1.0",
    summary="Fast, private PDF tools. No signup required.",
    description=(
        "PDFFlow processes documents without accounts and without permanent "
        "storage. Uploaded files live in a temporary directory under a "
        "generated name and are deleted automatically once they expire."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # no cookies, no sessions — nothing to send
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    expose_headers=["Content-Disposition"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = uuid.uuid4().hex[:12]
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def _error(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "requestId": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(PDFFlowError)
async def handle_known(request: Request, exc: PDFFlowError) -> JSONResponse:
    return _error(request, exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def handle_validation(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _error(request, 422, "invalid_request", "The request was not valid.")


@app.exception_handler(RateLimitExceeded)
async def handle_rate_limit(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return _error(
        request, 429, "rate_limited", "Too many requests. Please slow down and retry."
    )


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    """The last line of defence: log the real cause, return nothing about it.

    Tracebacks, file paths and stored filenames must never reach a client.
    """
    logger.exception(
        "unhandled_error",
        extra={
            "path": request.url.path,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    return _error(
        request, 500, "internal_error", "Something went wrong processing your request."
    )


app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(upload.router, prefix=settings.api_prefix)
app.include_router(jobs.router, prefix=settings.api_prefix)
app.include_router(download.router, prefix=settings.api_prefix)
