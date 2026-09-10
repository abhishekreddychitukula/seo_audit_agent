// Demonstration data for instant preview and offline resiliency

export const DEMO_Q1_AUDIT = [
  {
    metric: "llms_txt_missing",
    issue: "Missing /llms.txt AI File",
    page: "https://books.toscrape.com/llms.txt",
    severity: "low",
    evidence: "No active /llms.txt found (HTTP status 404).",
    suggested_fix: "Create an /llms.txt file to help AI search engines (Perplexity, SearchGPT, Gemini) index site knowledge."
  },
  {
    metric: "meta_description_empty",
    issue: "Empty Meta Description",
    page: "https://books.toscrape.com/",
    severity: "medium",
    evidence: "The <meta name=\"description\"> tag exists but its content attribute is empty.",
    suggested_fix: "Provide a descriptive summary in the content attribute of the meta description."
  },
  {
    metric: "heading_hierarchy_skip",
    issue: "Skipped Heading Level Hierarchy",
    page: "https://books.toscrape.com/",
    severity: "low",
    evidence: "Document contains 20 <h3> elements but no <h2> elements.",
    suggested_fix: "Maintain a logical heading hierarchy by nesting <h3> headings under <h2> sections."
  },
  {
    metric: "canonical_missing",
    issue: "Missing Canonical Tag",
    page: "https://books.toscrape.com/",
    severity: "medium",
    evidence: "No <link rel=\"canonical\"> tag found in the document <head>.",
    suggested_fix: "Add an explicit canonical link pointing to the preferred authoritative URL."
  },
  {
    metric: "image_dimensions_missing",
    issue: "Missing Image Dimensions (CLS Risk)",
    page: "https://books.toscrape.com/",
    severity: "low",
    evidence: "20 image(s) lack explicit width/height attributes (Cumulative Layout Shift risk).",
    suggested_fix: "Add width and height attributes to <img> elements to reserve layout space and prevent layout shifts."
  },
  {
    metric: "structured_data_missing",
    issue: "Missing Structured Data (Schema.org)",
    page: "https://books.toscrape.com/",
    severity: "low",
    evidence: "Homepage lacks Schema.org structured data (neither JSON-LD nor Microdata detected).",
    suggested_fix: "Implement Schema.org JSON-LD structured data (e.g. Organization, WebSite) for rich snippet eligibility."
  },
  {
    metric: "duplicate_title",
    issue: "Duplicate Page Title",
    page: "https://books.toscrape.com/",
    severity: "medium",
    evidence: "Title \"All products | Books to Scrape - Sandbox\" is identical across 2 crawled pages (['https://books.toscrape.com/', 'https://books.toscrape.com/index.html']).",
    suggested_fix: "Provide each page with a distinctive, descriptive title to prevent internal keyword cannibalization."
  },
  {
    metric: "slow_server_response",
    issue: "Slow Server Response Time",
    page: "https://books.toscrape.com/catalogue/category/books_1/index.html",
    severity: "low",
    evidence: "Server response time was 2.73s, exceeding the recommended 2.5s threshold.",
    suggested_fix: "Optimize server-side response times, implement caching, or use a CDN to reduce time to first byte."
  }
];

export const DEMO_Q1_SUMMARY = {
  health_score: 82,
  is_ai: false,
  provider: "Deterministic Rule-Based",
  overview: "Technical audit of books.toscrape.com identified 8 actionable opportunities across 25 crawled pages. Resolving missing canonical directives and empty meta descriptions will deliver immediate indexing clarity and CTR gains.",
  priority_actions: [
    {
      priority: 1,
      impact: "High",
      category: "Indexing",
      action: "Add Self-Referencing Canonical Tags",
      description: "Implement explicit <link rel=\"canonical\"> tags on the homepage and catalogue index to consolidate search ranking signals."
    },
    {
      priority: 2,
      impact: "High",
      category: "CTR & Metadata",
      action: "Populate Meta Descriptions & Differentiate Titles",
      description: "Add descriptive summaries to the empty description tag on root, and provide unique title tags to avoid keyword cannibalization."
    },
    {
      priority: 3,
      impact: "Medium",
      category: "AEO / AI Search",
      action: "Deploy /llms.txt for AI Engine Discovery",
      description: "Create an /llms.txt file at domain root to guide LLM search systems (Perplexity, SearchGPT) on product catalog structure."
    },
    {
      priority: 4,
      impact: "Medium",
      category: "Core Web Vitals",
      action: "Specify Image Width and Height Attributes",
      description: "Set explicit width and height dimensions on book thumbnail images to eliminate Cumulative Layout Shifts (CLS)."
    }
  ]
};

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

export const DEMO_Q2_OFFSITE = {
  status: "success",
  citation_health_score: 82,
  summary: "Autonomous web search detected external sandbox directory references and developer citations for Books to Scrape. While brand identity is uniformly maintained across developer listings, physical address and phone numbers are absent since this domain is maintained as an open web scraping playground.",
  citations: [
    {
      source: "GitHub Community & Projects",
      url: "https://github.com/topics/books-toscrape",
      name: "Books to Scrape",
      address: null,
      phone: null,
      match_status: "consistent",
      discrepancy_details: "Matches in-site brand name perfectly. Referenced in open-source scraper repositories."
    },
    {
      source: "ScrapingHub / Zyte Sandbox Directory",
      url: "https://www.zyte.com/blog/web-scraping-sandbox-sites",
      name: "Books to Scrape",
      address: null,
      phone: null,
      match_status: "consistent",
      discrepancy_details: "Referenced as canonical sandbox target for testing book catalog pagination and CSS selectors."
    },
    {
      source: "DataCamp Community Tutorials",
      url: "https://www.datacamp.com/tutorial/web-scraping-python-beautifulsoup",
      name: "Books to Scrape Sandbox",
      address: null,
      phone: null,
      match_status: "partial",
      discrepancy_details: "Listing includes 'Sandbox' descriptor suffix; canonical name is 'Books to Scrape'."
    }
  ],
  recommendations: [
    "If migrating to a commercial bookstore, claim and verify a Google Business Profile listing.",
    "Add Schema.org LocalBusiness or Bookstore JSON-LD markup on homepage to broadcast verified NAP signals.",
    "Register consistent business citations on major directory aggregators (Bing Places, Apple Maps, Yelp)."
  ],
  in_site_canonical: {
    name: "Books to Scrape",
    address: "Not stated on website",
    phone: "Not stated on website"
  }
};

export const DEMO_Q3_QA = {
  query: "What is the warning about prices and ratings on this website?",
  answer: "This is a demonstration sandbox website built strictly for testing web scrapers; all product prices and star ratings have been randomly generated and do not represent genuine market values.",
  url: "https://books.toscrape.com/",
  excerpt: "Warning! This is a demo website for web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning."
};
