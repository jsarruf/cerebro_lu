"""Chat orchestration for the API route."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from . import interpreter
from .adk_runtime import AdkRuntime
from .config import Settings, get_settings
from .logging_config import get_logger
from .services import SalesService
from .tools import sales_service

logger = get_logger("chat_service")


@dataclass(frozen=True, slots=True)
class ChatResult:
    """Assistant text plus the engine that actually produced it."""

    response: str
    engine: Literal["local", "adk"]


class ChatService:
    """Orchestrate history, engine selection, and safe ADK fallback."""

    def __init__(
        self,
        settings: Settings | None = None,
        service: SalesService | None = None,
        adk_runtime: AdkRuntime | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._service = service or sales_service
        self._adk = adk_runtime or AdkRuntime(
            timeout_seconds=self._settings.adk_timeout_seconds
        )

    async def reply(self, session_id: str, message: str) -> str:
        """Return one assistant response and persist both conversation sides."""

        result = await self.reply_with_metadata(session_id, message)
        return result.response

    async def reply_with_metadata(self, session_id: str, message: str) -> ChatResult:
        """Return the response and identify the engine used for this turn."""

        started_at = perf_counter()
        engine: Literal["local", "adk"] = "local"
        self._service.record_message(session_id, "user", message)

        if self._should_use_adk():
            try:
                response = await self._adk.ask(session_id, message)
                engine = "adk"
            except Exception as exc:
                logger.warning(
                    "adk_fallback",
                    extra={
                        "session_id": session_id,
                        "engine": "adk",
                        "error_type": type(exc).__name__,
                    },
                )
                response = interpreter.reply(
                    session_id,
                    message,
                    service=self._service,
                )
        else:
            response = interpreter.reply(
                session_id,
                message,
                service=self._service,
            )

        self._service.record_message(session_id, "assistant", response)
        logger.info(
            "chat_completed",
            extra={
                "session_id": session_id,
                "engine": engine,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        return ChatResult(response=response, engine=engine)

    def _should_use_adk(self) -> bool:
        if self._settings.chat_engine != "adk":
            return False
        if not self._settings.has_google_api_key:
            logger.warning(
                "adk_credentials_missing",
                extra={"engine": "adk"},
            )
            return False
        return self._adk.available()


chat_service = ChatService()


def get_chat_service() -> ChatService:
    """FastAPI dependency returning the process-wide chat service."""

    return chat_service
