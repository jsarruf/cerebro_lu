import asyncio
import unittest

from cerebro_lu.adk_agent.agent import root_agent
from cerebro_lu.adk_runtime import AdkRuntime


class AdkContractTest(unittest.TestCase):
    def test_adk_agent_is_configured_when_dependency_is_installed(self):
        self.assertIsNotNone(root_agent)
        self.assertEqual(root_agent.name, "cerebro_lu_sales_agent")
        tool_names = {tool.__name__ for tool in root_agent.tools}

        self.assertEqual(
            tool_names,
            {
                "add_product",
                "remove_product",
                "clear_cart",
                "get_cart",
                "checkout_pix",
                "get_order_status",
            },
        )

    def test_adk_prompt_includes_session_id_for_tools(self):
        captured = {}

        class FakePart:
            @staticmethod
            def from_text(text):
                captured["text"] = text
                return text

        class FakeContent:
            def __init__(self, role, parts):
                self.role = role
                self.parts = parts

        class FakeTypes:
            Content = FakeContent
            Part = FakePart

        session_id = "session-test-123"
        message = "adicionar 1 mochila"
        content = AdkRuntime._build_user_content(FakeTypes, session_id, message)

        self.assertEqual(content.role, "user")
        self.assertIn("session_id: session-test-123", captured["text"])
        self.assertIn("mensagem_do_usuario: adicionar 1 mochila", captured["text"])

    def test_adk_runtime_reports_availability(self):
        self.assertTrue(AdkRuntime().available())


class AdkRuntimeSessionTest(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_reuses_session_so_adk_keeps_context(self):
        class FakeSessionService:
            def __init__(self):
                self.created = []

            async def create_session(self, **kwargs):
                self.created.append(kwargs)

        class FakePart:
            text = "Resposta final"

        class FakeContent:
            parts = [FakePart()]

        class FakeEvent:
            content = FakeContent()

            @staticmethod
            def is_final_response():
                return True

        class FakeRunner:
            def __init__(self):
                self.session_service = FakeSessionService()
                self.messages = []

            async def run_async(self, **kwargs):
                self.messages.append(kwargs["new_message"])
                yield FakeEvent()

        runner = FakeRunner()
        runtime = AdkRuntime()
        runtime._runner = runner

        first = await runtime.ask("session-1", "primeira mensagem")
        second = await runtime.ask("session-1", "segunda mensagem")

        self.assertEqual(first, "Resposta final")
        self.assertEqual(second, "Resposta final")
        self.assertEqual(len(runner.session_service.created), 1)
        self.assertEqual(len(runner.messages), 2)

    async def test_runtime_enforces_turn_timeout(self):
        class FakeSessionService:
            async def create_session(self, **kwargs):
                return None

        class SlowRunner:
            session_service = FakeSessionService()

            async def run_async(self, **kwargs):
                await asyncio.sleep(0.02)
                if False:
                    yield None

        runtime = AdkRuntime(timeout_seconds=0.001)
        runtime._runner = SlowRunner()

        with self.assertRaises(TimeoutError):
            await runtime.ask("session-1", "ola")


if __name__ == "__main__":
    unittest.main()
