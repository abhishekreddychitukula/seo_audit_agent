import unittest
from unittest.mock import MagicMock, patch
from seo_audit_agent.ai_provider import AIProvider


class TestAIProvider(unittest.TestCase):
    def test_provider_disabled(self):
        ai = AIProvider(provider="none")
        self.assertFalse(ai.is_available)
        self.assertIsNone(ai.generate_text("test prompt"))
        self.assertEqual(
            ai.enhance_suggested_fix(
                metric="meta_description_missing",
                evidence="No description",
                page_title="Title",
                page_snippet="Snippet",
                default_fix="Add description.",
            ),
            "Add description.",
        )
        self.assertIsNone(ai.verify_and_refine_answer("test query", []))

    def test_provider_auto_without_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            ai = AIProvider(provider="auto")
            self.assertEqual(ai.provider, "none")
            self.assertFalse(ai.is_available)

    def test_gemini_resolution_with_key(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-gemini-key"}):
            ai = AIProvider(provider="gemini")
            self.assertEqual(ai.provider, "gemini")
            self.assertTrue(ai.is_available)
            self.assertEqual(ai.model, "gemini-1.5-flash")

    def test_groq_resolution_with_key(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-groq-key"}):
            ai = AIProvider(provider="groq")
            self.assertEqual(ai.provider, "groq")
            self.assertTrue(ai.is_available)
            self.assertEqual(ai.model, "llama-3.3-70b-versatile")

    def test_openai_resolution_with_key(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-openai-key"}):
            ai = AIProvider(provider="openai")
            self.assertEqual(ai.provider, "openai")
            self.assertTrue(ai.is_available)
            self.assertEqual(ai.model, "gpt-4o-mini")

    @patch("requests.post")
    def test_graceful_fallback_on_network_error(self, mock_post):
        mock_post.side_effect = Exception("Connection refused / timed out")
        ai = AIProvider(provider="gemini", api_key="dummy-key")
        result = ai.generate_text("test prompt")
        # Must return None and not raise exception
        self.assertIsNone(result)

    @patch("requests.post")
    def test_graceful_fallback_on_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 429
        mock_resp.text = "Rate limit exceeded"
        mock_post.return_value = mock_resp

        ai = AIProvider(provider="groq", api_key="dummy-key")
        result = ai.generate_text("test prompt")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
