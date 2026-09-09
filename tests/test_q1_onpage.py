import unittest
from seo_audit_agent.crawler import Page
from seo_audit_agent.q1_onpage import audit


class TestQ1OnPageAuditor(unittest.TestCase):
    def test_missing_title_and_h1(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            <p>Welcome to our simple web page with enough content to avoid thin content flag.</p>
        </body>
        </html>
        """
        page = Page(
            url="https://example.com/test",
            status=200,
            content_type="text/html",
            html=html,
            final_url="https://example.com/test",
        )
        findings = audit([page])
        metrics = {f["metric"] for f in findings}

        self.assertIn("title_missing", metrics)
        self.assertIn("h1_missing", metrics)
        self.assertIn("meta_description_missing", metrics)
        self.assertIn("canonical_missing", metrics)

    def test_title_and_description_length_checks(self):
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Short</title>
            <meta name="description" content="Too short">
            <link rel="canonical" href="https://example.com/page">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            <h1>Page Heading</h1>
            <p>Valid content body text goes here.</p>
        </body>
        </html>
        """
        page = Page(
            url="https://example.com/page",
            status=200,
            content_type="text/html",
            html=html,
            final_url="https://example.com/page",
        )
        findings = audit([page])
        metrics = {f["metric"] for f in findings}

        self.assertIn("title_too_short", metrics)
        self.assertIn("meta_description_too_short", metrics)

    def test_robots_noindex_and_image_alt(self):
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Valid Title Exceeding Fifteen Chars</title>
            <meta name="robots" content="noindex, follow">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="canonical" href="https://example.com/noindex-page">
        </head>
        <body>
            <h1>Valid Main Title</h1>
            <img src="/images/logo.png">
        </body>
        </html>
        """
        page = Page(
            url="https://example.com/noindex-page",
            status=200,
            content_type="text/html",
            html=html,
            final_url="https://example.com/noindex-page",
        )
        findings = audit([page])
        metrics = {f["metric"] for f in findings}

        self.assertIn("robots_noindex", metrics)
        self.assertIn("image_alt_missing", metrics)

    def test_duplicate_title_across_pages(self):
        html1 = """
        <!DOCTYPE html><html lang="en"><head><title>Duplicate Company Portal</title><link rel="canonical" href="https://example.com/1"></head><body><h1>H1</h1></body></html>
        """
        html2 = """
        <!DOCTYPE html><html lang="en"><head><title>Duplicate Company Portal</title><link rel="canonical" href="https://example.com/2"></head><body><h1>H2</h1></body></html>
        """
        p1 = Page("https://example.com/1", 200, "text/html", html1, "https://example.com/1")
        p2 = Page("https://example.com/2", 200, "text/html", html2, "https://example.com/2")
        findings = audit([p1, p2])
        dup_findings = [f for f in findings if f["metric"] == "duplicate_title"]
        self.assertEqual(len(dup_findings), 2)

    def test_new_metrics_depth_redirects_and_assets(self):
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Valid Document Title Here For Testing</title>
            <script src="/static/app.js"></script>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="canonical" href="https://example.com/sub">
        </head>
        <body>
            <h1>Main Topic</h1>
            <img src="/img/hero.png" alt="Hero banner">
            <img src="/img/1.png" alt="Img 1">
            <img src="/img/2.png" alt="Img 2">
            <img src="/img/3.png" alt="Img 3">
        </body>
        </html>
        """
        p = Page(
            url="https://example.com/sub",
            status=200,
            content_type="text/html",
            html=html,
            final_url="https://example.com/sub",
            depth=4,
            redirect_chain=[
                {"status": 301, "url": "http://example.com/sub"},
                {"status": 302, "url": "https://example.com/sub/"},
            ],
        )
        findings = audit([p])
        metrics = {f["metric"] for f in findings}

        self.assertIn("click_depth_high", metrics)
        self.assertIn("redirect_chain", metrics)
        self.assertIn("render_blocking_script", metrics)
        self.assertIn("image_dimensions_missing", metrics)


if __name__ == "__main__":
    unittest.main()
