import json
import logging
import os
import unittest
from unittest.mock import patch

from cerebro_lu.config import Settings
from cerebro_lu.logging_config import JsonFormatter


class SettingsTest(unittest.TestCase):
    def test_settings_are_loaded_from_environment(self):
        environment = {
            "CHAT_ENGINE": "adk",
            "ADK_MODEL": "gemini-2.5-flash",
            "ADK_TIMEOUT_SECONDS": "12.5",
            "LOG_LEVEL": "warning",
            "GOOGLE_API_KEY": "secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings.from_env()

        self.assertEqual(settings.chat_engine, "adk")
        self.assertEqual(settings.adk_timeout_seconds, 12.5)
        self.assertEqual(settings.log_level, "WARNING")

    def test_invalid_engine_is_rejected(self):
        with patch.dict(os.environ, {"CHAT_ENGINE": "invalid"}, clear=True):
            with self.assertRaisesRegex(ValueError, "CHAT_ENGINE"):
                Settings.from_env()

    def test_non_positive_timeout_is_rejected(self):
        with patch.dict(
            os.environ,
            {"CHAT_ENGINE": "local", "ADK_TIMEOUT_SECONDS": "0"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "ADK_TIMEOUT_SECONDS"):
                Settings.from_env()


class JsonFormatterTest(unittest.TestCase):
    def test_formatter_emits_structured_allowed_fields(self):
        record = logging.LogRecord(
            name="cerebro_lu.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="tool_completed",
            args=(),
            exc_info=None,
        )
        record.session_id = "session-1"
        record.tool = "add_product"
        record.duration_ms = 1.25
        record.api_key = "must-not-be-logged"

        payload = json.loads(JsonFormatter().format(record))

        self.assertEqual(payload["event"], "tool_completed")
        self.assertEqual(payload["session_id"], "session-1")
        self.assertEqual(payload["tool"], "add_product")
        self.assertNotIn("api_key", payload)


if __name__ == "__main__":
    unittest.main()
