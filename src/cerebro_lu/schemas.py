"""HTTP schemas for the conversational API."""

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Request body accepted by POST /api/v1/chat."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "session_id": "user-session-12345",
                "message": "Quero adicionar 2 tenis de corrida ao carrinho.",
            }
        },
    )

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
        description="Identificador estavel usado para carrinho e historico.",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=2_000,
        description="Mensagem em linguagem natural enviada ao agente.",
    )


class ChatResponse(BaseModel):
    """Response body returned by POST /api/v1/chat."""

    session_id: str
    response: str


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str


class ErrorDetail(BaseModel):
    """Stable, user-safe API error."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Envelope used by validation and internal errors."""

    error: ErrorDetail
