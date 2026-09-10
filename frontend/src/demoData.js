// Demonstration data for instant preview and offline resiliency

export const DEMO_Q1_AUDIT = [
  {
    metric: "llms_txt_missing",
    page: "https://books.toscrape.com/llms.txt",
    severity: "low",
    evidence: "No active /llms.txt found (HTTP status 404).",
    suggested_fix: "Create an /llms.txt file to help AI search engines (Perplexity, SearchGPT, Gemini) index site knowledge."
  },
  {
    metric: "meta_description_empty",
    page: "https://books.toscrape.com/",
    severity: "medium",
    evidence: "The <meta name=\"description\"> tag exists but its content attribute is empty.",
    suggested_fix: "Provide a descriptive summary in the content attribute of the meta description."
  },
  {
    metric: "heading_hierarchy_skip",
    page: "https://books.toscrape.com/",
    severity: "low",
    evidence: "Document contains 20 <h3> elements but no <h2> elements.",
    suggested_fix: "Maintain a logical heading hierarchy by nesting <h3> headings under <h2> sections."
  },
  {
    metric: "canonical_missing",
    page: "https://books.toscrape.com/",
    severity: "medium",
    evidence: "No <link rel=\"canonical\"> tag found in the document <head>.",
    suggested_fix: "Add an explicit canonical link pointing to the preferred authoritative URL."
  },
  {
    metric: "image_dimensions_missing",
    page: "https://books.toscrape.com/",
    severity: "low",
    evidence: "20 image(s) lack explicit width/height attributes (Cumulative Layout Shift risk).",
    suggested_fix: "Add width and height attributes to <img> elements to reserve layout space and prevent layout shifts."
  },
  {
    metric: "structured_data_missing",
    page: "https://books.toscrape.com/",
    severity: "low",
    evidence: "Homepage lacks Schema.org structured data (neither JSON-LD nor Microdata detected).",
    suggested_fix: "Implement Schema.org JSON-LD structured data (e.g. Organization, WebSite) for rich snippet eligibility."
  },
  {
    metric: "duplicate_title",
    page: "https://books.toscrape.com/",
    severity: "medium",
    evidence: "Title \"All products | Books to Scrape - Sandbox\" is identical across 2 crawled pages (['https://books.toscrape.com/', 'https://books.toscrape.com/index.html']).",
    suggested_fix: "Provide each page with a distinctive, descriptive title to prevent internal keyword cannibalization."
  },
  {
    metric: "slow_server_response",
    page: "https://books.toscrape.com/catalogue/category/books_1/index.html",
    severity: "low",
    evidence: "Server response time was 2.73s, exceeding the recommended 2.5s threshold.",
    suggested_fix: "Optimize server-side response times, implement caching, or use a CDN to reduce time to first byte."
  }
];

export const DEMO_Q2_NAP = [
  {
    field: "name",
    pages_compared: [
      "https://books.toscrape.com/",
      "https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
      "https://books.toscrape.com/catalogue/category/books_1/index.html",
      "https://books.toscrape.com/index.html"
    ],
    values: [
      {
        value: "Books to Scrape",
        normalized: "books to scrape",
        pages: [
          "https://books.toscrape.com/",
          "https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
          "https://books.toscrape.com/catalogue/category/books_1/index.html",
          "https://books.toscrape.com/index.html"
        ],
        occurrences: 25,
        sources: ["header_brand"]
      }
    ],
    normalized_values: ["books to scrape"],
    confidence: 0.9,
    confidence_explanation: "Consistent name verified across 25 page(s) and 1 source(s) (header_brand) with 0 discrepancies.",
    verdict: "consistent"
  },
  {
    field: "address",
    pages_compared: [],
    values: [],
    normalized_values: [],
    confidence: 0.0,
    confidence_explanation: "No business address indicators were detected on any crawled page.",
    verdict: "not_found"
  },
  {
    field: "phone",
    pages_compared: [],
    values: [],
    normalized_values: [],
    confidence: 0.0,
    confidence_explanation: "No business phone indicators were detected on any crawled page.",
    verdict: "not_found"
  }
];

export const DEMO_Q3_QA = {
  query: "What is the warning about prices and ratings on this website?",
  url: "https://books.toscrape.com/",
  excerpt: "Warning! This is a demo website for web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning."
};
