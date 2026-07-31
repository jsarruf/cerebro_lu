"""Optional Google ADK runtime adapter."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import perf_counter

from .logging_config import get_logger

logger = get_logger("adk_runtime")


@dataclass
class AdkRuntime:
    """Thin wrapper around Google ADK Runner.

    The project defaults to the local deterministic engine so the challenge can
    be run and tested without external credentials. When CHAT_ENGINE=adk and
    google-adk is installed, this class runs the same tools through ADK.
    """

    app_name: str = "cerebro_lu"
    timeout_seconds: float = 30.0
    _runner: object | None = field(default=None, init=False)
    _session_ids: set[str] = field(default_factory=set, init=False)
    _session_lock: asyncio.Lock = field(
        default_factory=asyncio.Lock,
        init=False,
        repr=False,
    )

    def available(self) -> bool:
        try:
            import google.adk  # noqa: F401
            import google.genai  # noqa: F401
        except ModuleNotFoundError:
            return False
        return True

    async def ask(self, session_id: str, message: str) -> str:
        """Run one turn while reusing the ADK session history."""

        if self._runner is None:
            self._runner = self._build_runner()

        from google.genai import types

        runner = self._runner
        await self._ensure_session(runner, session_id)
        started_at = perf_counter()

        async with asyncio.timeout(self.timeout_seconds):
            final_text = await self._run_turn(
                runner,
                self._build_user_content(types, session_id, message),
                session_id,
            )

        logger.info(
            "adk_turn_completed",
            extra={
                "session_id": session_id,
                "engine": "adk",
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        return final_text or "Nao consegui gerar uma resposta final para esta mensagem."

    async def _ensure_session(self, runner: object, session_id: str) -> None:
        if session_id in self._session_ids:
            return
        async with self._session_lock:
            if session_id in self._session_ids:
                return
            await runner.session_service.create_session(
                app_name=self.app_name,
                user_id=session_id,
                session_id=session_id,
            )
            self._session_ids.add(session_id)

    @staticmethod
    async def _run_turn(
        runner: object,
        content: object,
        session_id: str,
    ) -> str:
        final_text = ""
        async for event in runner.run_async(
            user_id=session_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text or ""
        return final_text

    @staticmethod
    def _build_user_content(types: object, session_id: str, message: str) -> object:
        return types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=(
                        f"session_id: {session_id}\n"
                        f"mensagem_do_usuario: {message}"
                    )
                )
            ],
        )

    def _build_runner(self) -> object:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        from .adk_agent.agent import root_agent

        return Runner(
            agent=root_agent,
            app_name=self.app_name,
            session_service=InMemorySessionService(),
        )
