"""FastAPI entry point for the challenge API."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Annotated

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHttpException
from starlette.responses import Response

from .chat_service import ChatService, get_chat_service
from .config import get_settings
from .logging_config import configure_logging, get_logger
from .schemas import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HealthResponse,
)

STATIC_DIR = Path(__file__).parent / "static"
settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("api")

app = FastAPI(
    title="Cerebro da Lu API",
    description="API REST conversacional para um agente de vendas inteligente.",
    version="0.1.0",
    openapi_tags=[
        {
            "name": "Chat",
            "description": "Conversa com o agente e preserva estado por session_id.",
        },
        {
            "name": "Operacao",
            "description": "Endpoints operacionais da aplicacao.",
        },
    ],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def observe_request(request: Request, call_next) -> Response:
    """Measure requests and emit structured operational logs."""

    started_at = perf_counter()
    request.state.started_at = started_at
    response = await call_next(request)
    duration_ms = round((perf_counter() - started_at) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    logger.info(
        "http_request_completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return a stable response for invalid JSON and payloads."""

    invalid_json = any(error.get("type") == "json_invalid" for error in exc.errors())
    code = "invalid_json" if invalid_json else "validation_error"
    message = "JSON invalido." if invalid_json else "Payload invalido."
    logger.warning(
        "request_validation_failed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "error_type": code,
        },
    )
    return _error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        code,
        message,
    )


@app.exception_handler(StarletteHttpException)
async def http_error_handler(
    request: Request,
    exc: StarletteHttpException,
) -> JSONResponse:
    """Hide framework internals behind a stable error envelope."""

    logger.warning(
        "http_error",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
            "error_type": "http_error",
        },
    )
    return _error_response(
        exc.status_code,
        "http_error",
        "Recurso nao encontrado."
        if exc.status_code == status.HTTP_404_NOT_FOUND
        else "Nao foi possivel concluir a solicitacao.",
    )


@app.exception_handler(Exception)
async def internal_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Log unexpected failures without exposing stack traces to clients."""

    duration_ms = round(
        (perf_counter() - getattr(request.state, "started_at", perf_counter()))
        * 1000,
        2,
    )
    logger.exception(
        "unhandled_error",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "error_type": type(exc).__name__,
            "duration_ms": duration_ms,
        },
    )
    response = _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "internal_error",
        "Erro interno. Tente novamente mais tarde.",
    )
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    return response


@app.get("/", include_in_schema=False)
async def demo() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-cache"},
    )


@app.get(
    "/health",
    tags=["Operacao"],
    summary="Verificar disponibilidade",
    response_model=HealthResponse,
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        engine=settings.chat_engine,
        model=settings.adk_model if settings.chat_engine == "adk" else None,
        google_api_configured=settings.has_google_api_key,
    )


@app.post(
    "/api/v1/chat",
    tags=["Chat"],
    summary="Conversar com o agente de vendas",
    description=(
        "Processa uma mensagem mantendo carrinho e historico vinculados ao "
        "session_id informado."
    ),
    response_model=ChatResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "JSON ou payload invalido.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Falha interna tratada.",
        },
    },
)
async def chat(
    payload: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    result = await service.reply_with_metadata(payload.session_id, payload.message)
    return ChatResponse(
        session_id=payload.session_id,
        response=result.response,
        engine=result.engine,
        model=settings.adk_model if result.engine == "adk" else None,
    )


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(error={"code": code, "message": message})
    return JSONResponse(status_code=status_code, content=payload.model_dump())
