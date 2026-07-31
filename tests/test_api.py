import re
import unittest

from fastapi.testclient import TestClient

from cerebro_lu.chat_service import get_chat_service
from cerebro_lu.main import app
from cerebro_lu.tools import store


class ChatApiTest(unittest.TestCase):
    def setUp(self):
        store.reset()
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_chat_endpoint_adds_item_and_checks_out(self):
        add = self.client.post(
            "/api/v1/chat",
            json={
                "session_id": "api-session-1",
                "message": "Quero adicionar 2 tenis de corrida ao meu carrinho.",
            },
        )
        checkout = self.client.post(
            "/api/v1/chat",
            json={"session_id": "api-session-1", "message": "fechar pedido no pix"},
        )

        self.assertEqual(add.status_code, 200)
        self.assertEqual(checkout.status_code, 200)
        self.assertEqual(add.json()["session_id"], "api-session-1")
        self.assertIn("Adicionei 2 tenis de corrida", add.json()["response"])
        self.assertIn("PIX copia-e-cola", checkout.json()["response"])
        self.assertRegex(checkout.json()["response"], r"PED-\d{8}-[0-9A-F]{6}")

    def test_invalid_payload_returns_validation_error(self):
        response = self.client.post("/api/v1/chat", json={"session_id": "", "message": ""})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_invalid_json_returns_stable_error(self):
        response = self.client.post(
            "/api/v1/chat",
            content="{",
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {"error": {"code": "invalid_json", "message": "JSON invalido."}},
        )

    def test_session_with_unsafe_characters_is_rejected(self):
        response = self.client.post(
            "/api/v1/chat",
            json={"session_id": "../session", "message": "ola"},
        )

        self.assertEqual(response.status_code, 422)

    def test_response_includes_processing_time_header(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.headers.get("X-Process-Time-Ms"))

    def test_unknown_route_returns_stable_error(self):
        response = self.client.get("/missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "http_error")

    def test_internal_error_does_not_expose_exception(self):
        class FailingChatService:
            async def reply(self, session_id, message):
                raise RuntimeError("sensitive internal detail")

        app.dependency_overrides[get_chat_service] = lambda: FailingChatService()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/api/v1/chat",
            json={"session_id": "session-1", "message": "ola"},
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "internal_error")
        self.assertNotIn("sensitive", response.text)
        self.assertIsNotNone(response.headers.get("X-Process-Time-Ms"))

    def test_openapi_documents_chat_errors_and_tags(self):
        schema = self.client.get("/openapi.json").json()
        operation = schema["paths"]["/api/v1/chat"]["post"]

        self.assertEqual(operation["tags"], ["Chat"])
        self.assertIn("422", operation["responses"])
        self.assertIn("500", operation["responses"])

    def test_demo_page_is_served(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Cerebro da Lu", response.text)
        self.assertIn("/static/app.js", response.text)

    def test_demo_static_assets_are_served(self):
        response = self.client.get("/static/styles.css")

        self.assertEqual(response.status_code, 200)
        self.assertIn(".workspace", response.text)


if __name__ == "__main__":
    unittest.main()
