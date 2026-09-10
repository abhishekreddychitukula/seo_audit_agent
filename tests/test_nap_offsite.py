import unittest
from unittest.mock import MagicMock, patch
from seo_audit_agent.nap_offsite import (
    extract_in_site_canonical,
    search_web,
    audit_offsite_nap,
)


class TestOffsiteNAP(unittest.TestCase):
    def test_extract_in_site_canonical_standard(self):
        in_site_report = [
            {
                "field": "name",
                "values": [{"value": "Acme Widgets", "normalized": "acme widgets"}],
                "verdict": "consistent",
            },
            {
                "field": "address",
                "values": [{"value": "456 Market St, Austin, TX", "normalized": "456 market st"}],
                "verdict": "consistent",
            },
            {
                "field": "phone",
                "values": [{"value": "555-123-4567", "normalized": "5551234567"}],
                "verdict": "consistent",
            },
        ]
        canonical = extract_in_site_canonical(in_site_report)
        self.assertEqual(canonical["name"], "Acme Widgets")
        self.assertEqual(canonical["address"], "456 Market St, Austin, TX")
        self.assertEqual(canonical["phone"], "555-123-4567")

    def test_extract_in_site_canonical_empty(self):
        canonical = extract_in_site_canonical([])
        self.assertEqual(canonical, {"name": "", "address": "", "phone": ""})

    def test_search_web_tool_exists(self):
        # search_web is a LangChain @tool
        self.assertTrue(hasattr(search_web, "invoke") or callable(search_web))

    @patch("seo_audit_agent.nap_offsite.get_llm")
    def test_audit_offsite_no_llm(self, mock_get_llm):
        mock_get_llm.return_value = (None, "None")
        res = audit_offsite_nap("https://example.com", [])
        self.assertEqual(res["status"], "no_llm")
        self.assertIsNone(res["citation_health_score"])
        self.assertIn("recommendations", res)

    @patch("seo_audit_agent.nap_offsite.get_llm")
    def test_audit_offsite_mocked_llm(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        # Step 1: Model issues a tool call
        tool_call_resp = MagicMock()
        tool_call_resp.tool_calls = [
            {"id": "call_123", "name": "search_web", "args": {"query": "Acme Widgets directory"}}
        ]
        mock_bound.invoke.return_value = tool_call_resp

        # Step 2: Final synthesis step
        final_synth_resp = MagicMock()
        final_synth_resp.content = (
            '{"citation_health_score": 90, "summary": "Found verified listing on Yelp.", '
            '"citations": [{"source": "Yelp", "url": "https://yelp.com/biz/acme", "name": "Acme Widgets", '
            '"address": "456 Market St", "phone": "555-123-4567", "match_status": "consistent", '
            '"discrepancy_details": "Exact match"}], "recommendations": ["Keep profile active."]}'
        )
        mock_llm.invoke.return_value = final_synth_resp

        mock_get_llm.return_value = (mock_llm, "Groq (qwen/qwen3.6-27b)")

        with patch("seo_audit_agent.nap_offsite.DDGS") as mock_ddgs_cls:
            mock_instance = MagicMock()
            mock_instance.text.return_value = [
                {"title": "Acme Widgets on Yelp", "href": "https://yelp.com/biz/acme", "body": "456 Market St, Austin, TX. Phone: 555-123-4567"}
            ]
            mock_ddgs_cls.return_value = mock_instance

            res = audit_offsite_nap("https://example.com", [
                {"field": "name", "values": [{"value": "Acme Widgets"}]}
            ])

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["citation_health_score"], 90)
        self.assertEqual(len(res["citations"]), 1)
        self.assertEqual(res["citations"][0]["source"], "Yelp")
        self.assertEqual(res["citations"][0]["match_status"], "consistent")


if __name__ == "__main__":
    unittest.main()
