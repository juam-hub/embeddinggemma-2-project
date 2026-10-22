import unittest
from unittest.mock import patch, MagicMock
from core.cloud_llm import (
    CLOUD_PROVIDERS,
    get_provider_endpoint,
    format_messages_for_cloud,
    test_cloud_connection,
    stream_cloud_chat,
)


class TestCloudLLM(unittest.TestCase):
    def test_provider_endpoint(self):
        self.assertEqual(
            get_provider_endpoint("groq"),
            "https://api.groq.com/openai/v1/chat/completions"
        )
        self.assertEqual(
            get_provider_endpoint("openai"),
            "https://api.openai.com/v1/chat/completions"
        )
        self.assertEqual(
            get_provider_endpoint("custom", "http://my-proxy:8000/v1"),
            "http://my-proxy:8000/v1/chat/completions"
        )

    def test_format_messages_no_images(self):
        raw = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        formatted = format_messages_for_cloud(raw)
        self.assertEqual(len(formatted), 2)
        self.assertEqual(formatted[0]["role"], "system")
        self.assertEqual(formatted[1]["content"], "Hello!")

    def test_test_connection_empty_key(self):
        success, msg = test_cloud_connection("groq", "", "llama-3.3-70b-versatile")
        self.assertFalse(success)
        self.assertIn("vacía", msg)

    @patch("core.cloud_llm.requests.post")
    def test_test_connection_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        success, msg = test_cloud_connection("groq", "gsk_test123", "llama-3.3-70b-versatile")
        self.assertTrue(success)
        self.assertIn("exitosa", msg.lower())

    @patch("core.cloud_llm.requests.post")
    def test_test_connection_invalid_key(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        success, msg = test_cloud_connection("openai", "invalid_key", "gpt-4o-mini")
        self.assertFalse(success)
        self.assertIn("401", msg)

    @patch("core.cloud_llm.requests.post")
    def test_stream_cloud_chat(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = [
            "data: {\"choices\": [{\"delta\": {\"content\": \"Hola\"}}]}",
            "data: {\"choices\": [{\"delta\": {\"content\": \" mundo\"}}]}",
            "data: [DONE]"
        ]
        mock_post.return_value = mock_resp

        messages = [{"role": "user", "content": "¿Hola?"}]
        stream = stream_cloud_chat(messages, "groq", "gsk_123", "llama-3.3-70b-versatile")
        chunks = list(stream)
        self.assertEqual(chunks, ["Hola", " mundo"])


if __name__ == "__main__":
    unittest.main()
