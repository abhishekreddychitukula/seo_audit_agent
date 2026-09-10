import os
import unittest
from unittest.mock import MagicMock, patch
from seo_audit_agent.ai_provider import (
    AIProvider,
    generate_audit_summary,
    answer_query,
    get_llm,
    deterministic_seo_summary,
)


class TestAIProvider(unittest.TestCase):
    def test_no_keys_returns_none_no_hardcoded_summary(self):
        """CRITICAL: Verifies that without API keys, NO fake/hardcoded summary is produced."""
        with patch("seo_audit_agent.ai_provider.reload_env", return_value={}), patch.dict("os.environ", {}, clear=True):
            findings = [
                {"metric": "missing_title", "severity": "high", "evidence": "No title tag"},
            ]
            summary = generate_audit_summary(findings, "https://example.com")
            # Must return None so the frontend knows no AI summary exists!
            self.assertIsNone(summary)

    def test_empty_findings_returns_none(self):
        self.assertIsNone(generate_audit_summary([], "https://example.com"))

    def test_answer_query_empty_passages(self):
        self.assertIsNone(answer_query("test query", []))

    def test_get_llm_resolution_with_key(self):
        with patch("seo_audit_agent.ai_provider.reload_env", return_value={"GROQ_API_KEY": "gsk_testvalidkey12345678"}):
            llm, provider = get_llm()
            self.assertIsNotNone(llm)
            self.assertEqual(provider, "Groq")

    def test_get_llm_without_key(self):
        with patch("seo_audit_agent.ai_provider.reload_env", return_value={}), patch.dict("os.environ", {}, clear=True):
            llm, provider = get_llm()
            self.assertIsNone(llm)
            self.assertIsNone(provider)

    def test_deterministic_seo_summary_helper(self):
        findings = [
            {"metric": "canonical_missing", "severity": "critical", "evidence": "No canonical", "suggested_fix": "Add canonical"},
            {"metric": "meta_description_empty", "severity": "medium", "evidence": "Empty desc", "suggested_fix": "Add description"},
        ]
        res = deterministic_seo_summary(findings, "https://example.com")
        self.assertIn("health_score", res)
        self.assertIn("overview", res)
        self.assertIn("priority_actions", res)
        self.assertTrue(len(res["priority_actions"]) >= 1)

    def test_backward_compatible_wrapper(self):
        ai = AIProvider(provider="none")
        self.assertEqual(
            ai.enhance_suggested_fix(
                metric="meta_description_missing",
                default_fix="Add description.",
            ),
            "Add description.",
        )
        self.assertIsNone(ai.generate_seo_summary([], "https://example.com"))
        self.assertIsNone(ai.find_relevant_answer("test", []))


if __name__ == "__main__":
    unittest.main()
