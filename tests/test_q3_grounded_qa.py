import unittest
from seo_audit_agent.q3_grounded_qa import (
    PassageDoc,
    compute_bm25_and_coverage,
    extract_passages_from_html,
    extract_query_tokens,
    simple_stem,
)


class TestQ3GroundedQA(unittest.TestCase):
    def test_simple_stem(self):
        self.assertEqual(simple_stem("services"), simple_stem("service"))
        self.assertEqual(simple_stem("pricing"), simple_stem("price"))
        self.assertEqual(simple_stem("returned"), simple_stem("return"))
        self.assertEqual(simple_stem("companies"), simple_stem("company"))

    def test_extract_query_tokens(self):
        tokens = extract_query_tokens("What are your business return policies?")
        self.assertIn("business", tokens)
        self.assertIn("return", tokens)
        self.assertIn("policies", tokens)
        self.assertNotIn("what", tokens)
        self.assertNotIn("are", tokens)

    def test_composite_faq_extraction(self):
        html = """
        <html><body>
            <h3>What is the warranty period?</h3>
            <p>All hardware items come with a comprehensive 2-year warranty from date of purchase.</p>
        </body></html>
        """
        passages = extract_passages_from_html(html)
        self.assertTrue(any("What is the warranty period?: All hardware items" in p for p in passages))

    def test_bm25_relevance_matching(self):
        doc1 = PassageDoc(
            url="https://example.com/returns",
            text="Customers may return any unopened item within 30 days for a full refund.",
        )
        doc2 = PassageDoc(
            url="https://example.com/about",
            text="Our executive leadership team has fifty years of industry experience.",
        )
        q_tokens = extract_query_tokens("return policy and refund window")
        doc_freqs = {"return": 1, "refund": 1, "team": 1}

        score1, cov1 = compute_bm25_and_coverage(q_tokens, doc1, doc_freqs, 2, 10.0)
        score2, cov2 = compute_bm25_and_coverage(q_tokens, doc2, doc_freqs, 2, 10.0)

        self.assertGreater(score1, score2)
        self.assertGreater(cov1, cov2)

    def test_refusal_on_irrelevant_query(self):
        # When query terms do not match document tokens, coverage and score must be near zero
        doc = PassageDoc(
            url="https://example.com/cookies",
            text="We bake fresh chocolate chip cookies every morning at six o'clock.",
        )
        q_tokens = extract_query_tokens("quantum physics relativistic spacetime equations")
        doc_freqs = {}
        score, cov = compute_bm25_and_coverage(q_tokens, doc, doc_freqs, 1, 10.0)

        self.assertEqual(score, 0.0)
        self.assertEqual(cov, 0.0)


if __name__ == "__main__":
    unittest.main()
