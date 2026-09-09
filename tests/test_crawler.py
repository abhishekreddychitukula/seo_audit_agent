import unittest
from seo_audit_agent.crawler import (
    is_crawlable_link,
    normalize_url,
    same_site,
    url_priority_score,
)


class TestCrawlerUtils(unittest.TestCase):
    def test_normalize_url(self):
        self.assertEqual(
            normalize_url("https://example.com/about#team"),
            "https://example.com/about",
        )
        self.assertEqual(
            normalize_url("/contact", base="https://example.com/home"),
            "https://example.com/contact",
        )
        self.assertEqual(
            normalize_url("HTTPS://Example.COM:443/Path//Sub"),
            "https://example.com/Path/Sub",
        )

    def test_same_site(self):
        self.assertTrue(same_site("https://example.com/about", "https://example.com/"))
        self.assertTrue(same_site("https://www.example.com/contact", "https://example.com/"))
        self.assertFalse(same_site("https://otherdomain.com", "https://example.com"))
        self.assertFalse(same_site("mailto:info@example.com", "https://example.com"))

    def test_is_crawlable_link(self):
        self.assertTrue(is_crawlable_link("https://example.com/about-us"))
        self.assertTrue(is_crawlable_link("https://example.com/services/"))
        self.assertFalse(is_crawlable_link("https://example.com/document.pdf"))
        self.assertFalse(is_crawlable_link("https://example.com/banner.png"))
        self.assertFalse(is_crawlable_link("https://example.com/style.css"))

    def test_url_priority_score(self):
        contact_score = url_priority_score("https://example.com/contact-us")
        blog_score = url_priority_score("https://example.com/blog/article-1")
        self.assertGreater(contact_score, blog_score)


if __name__ == "__main__":
    unittest.main()
