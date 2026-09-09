import unittest
from seo_audit_agent.crawler import Page
from seo_audit_agent.nap import (
    audit_nap,
    norm_address,
    norm_name,
    norm_phone,
)


class TestNAPChecker(unittest.TestCase):
    def test_phone_normalization(self):
        self.assertEqual(norm_phone("+1 (555) 234-5678"), "5552345678")
        self.assertEqual(norm_phone("555.234.5678"), "5552345678")
        self.assertEqual(norm_phone("1-555-234-5678"), "5552345678")
        self.assertEqual(norm_phone("5552345678"), "5552345678")

    def test_address_normalization(self):
        addr1 = "100 North Main Street, Suite 200, Springfield, IL 62701"
        addr2 = "100 N. Main St., Ste. 200, Springfield, IL 62701"
        self.assertEqual(norm_address(addr1), norm_address(addr2))

    def test_name_normalization(self):
        self.assertEqual(norm_name("Acme Innovations, LLC"), "acme innovations")
        self.assertEqual(norm_name("Acme Innovations Inc."), "acme innovations")
        self.assertEqual(norm_name("Acme Innovations"), "acme innovations")

    def test_nap_consistency_across_pages(self):
        html1 = """
        <!DOCTYPE html><html><head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "LocalBusiness",
          "name": "Acme Widgets Inc.",
          "telephone": "+1-800-555-0199",
          "address": {
            "@type": "PostalAddress",
            "streetAddress": "456 Market Boulevard",
            "addressLocality": "Austin",
            "addressRegion": "TX",
            "postalCode": "78701"
          }
        }
        </script>
        </head><body><h1>Home</h1></body></html>
        """
        html2 = """
        <!DOCTYPE html><html><body>
        <footer>
            <p>Contact Acme Widgets at <a href="tel:800-555-0199">800-555-0199</a></p>
            <address>456 Market Blvd., Austin, TX 78701</address>
        </footer>
        </body></html>
        """
        p1 = Page("https://example.com/", 200, "text/html", html1, "https://example.com/")
        p2 = Page("https://example.com/contact", 200, "text/html", html2, "https://example.com/contact")

        report = audit_nap([p1, p2])
        field_map = {item["field"]: item for item in report}

        self.assertEqual(field_map["phone"]["verdict"], "consistent")
        self.assertEqual(field_map["address"]["verdict"], "consistent")
        self.assertEqual(field_map["name"]["verdict"], "consistent")
        self.assertGreaterEqual(field_map["phone"]["confidence"], 0.85)
        self.assertTrue(len(field_map["phone"]["confidence_explanation"]) > 20)

    def test_nap_mismatch_detection(self):
        html1 = '<html><body><a href="tel:555-111-2222">Call Us</a></body></html>'
        html2 = '<html><body><a href="tel:555-999-8888">Call Us</a></body></html>'
        p1 = Page("https://example.com/1", 200, "text/html", html1, "https://example.com/1")
        p2 = Page("https://example.com/2", 200, "text/html", html2, "https://example.com/2")

        report = audit_nap([p1, p2])
        field_map = {item["field"]: item for item in report}
        self.assertEqual(field_map["phone"]["verdict"], "mismatch")


if __name__ == "__main__":
    unittest.main()
