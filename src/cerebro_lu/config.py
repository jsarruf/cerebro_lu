"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, cast

from dotenv import load_dotenv

ChatEngine = Literal["local", "adk"]

load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime settings."""

    chat_engine: ChatEngine = "local"
    adk_model: str = "gemini-3.6-flash"
    adk_timeout_seconds: float = 30.0
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables."""

        engine_value = os.getenv("CHAT_ENGINE", "local").strip().lower()
        if engine_value not in {"local", "adk"}:
            raise ValueError("CHAT_ENGINE deve ser 'local' ou 'adk'.")

        timeout_value = float(os.getenv("ADK_TIMEOUT_SECONDS", "30"))
        if timeout_value <= 0:
            raise ValueError("ADK_TIMEOUT_SECONDS deve ser maior que zero.")

        return cls(
            chat_engine=cast(ChatEngine, engine_value),
            adk_model=os.getenv("ADK_MODEL", "gemini-3.6-flash").strip()
            or "gemini-3.6-flash",
            adk_timeout_seconds=timeout_value,
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
        )

    @property
    def has_google_api_key(self) -> bool:
        """Return whether ADK credentials are present without exposing them."""

        return bool(os.getenv("GOOGLE_API_KEY", "").strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable settings."""

    return Settings.from_env()
