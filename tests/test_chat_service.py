import os
import unittest
from unittest.mock import patch

from cerebro_lu.chat_service import ChatService
from cerebro_lu.config import Settings
from cerebro_lu.repository import InMemorySalesRepository
from cerebro_lu.services import SalesService


class FakeAdkRuntime:
    def __init__(self, response="Resposta do ADK", error=None):
        self.response = response
        self.error = error
        self.calls = []

    def available(self):
        return True

    async def ask(self, session_id, message):
        self.calls.append((session_id, message))
        if self.error:
            raise self.error
        return self.response


class ChatServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.sales_service = SalesService(InMemorySalesRepository())

    async def test_local_engine_persists_user_and_assistant_once(self):
        service = ChatService(
            settings=Settings(chat_engine="local"),
            service=self.sales_service,
            adk_runtime=FakeAdkRuntime(),
        )

        response = await service.reply("session-1", "adicionar 1 mochila")
        history = self.sales_service.get_history("session-1")

        self.assertIn("Adicionei 1 mochila", response)
        self.assertEqual([message.role for message in history], ["user", "assistant"])
        self.assertEqual(len(history), 2)

    async def test_adk_engine_persists_application_history(self):
        runtime = FakeAdkRuntime()
        service = ChatService(
            settings=Settings(chat_engine="adk"),
            service=self.sales_service,
            adk_runtime=runtime,
        )

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            response = await service.reply("session-1", "ola")

        history = self.sales_service.get_history("session-1")
        self.assertEqual(response, "Resposta do ADK")
        self.assertEqual(runtime.calls, [("session-1", "ola")])
        self.assertEqual(
            [message.content for message in history],
            ["ola", "Resposta do ADK"],
        )

    async def test_adk_failure_falls_back_without_duplicating_history(self):
        runtime = FakeAdkRuntime(error=RuntimeError("provider unavailable"))
        service = ChatService(
            settings=Settings(chat_engine="adk"),
            service=self.sales_service,
            adk_runtime=runtime,
        )

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            response = await service.reply("session-1", "adicionar 1 camiseta")

        history = self.sales_service.get_history("session-1")
        self.assertIn("Adicionei 1 camiseta", response)
        self.assertEqual(len(history), 2)

    async def test_missing_credentials_uses_local_engine(self):
        runtime = FakeAdkRuntime()
        service = ChatService(
            settings=Settings(chat_engine="adk"),
            service=self.sales_service,
            adk_runtime=runtime,
        )

        with patch.dict(os.environ, {}, clear=True):
            response = await service.reply("session-1", "ver meu carrinho")

        self.assertEqual(response, "Seu carrinho esta vazio no momento.")
        self.assertEqual(runtime.calls, [])


if __name__ == "__main__":
    unittest.main()
