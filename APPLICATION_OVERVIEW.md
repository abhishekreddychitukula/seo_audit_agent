# Comprehensive Application Architecture & Technical Overview

This document provides an exhaustive, component-by-component explanation of how the **SEO Audit Agent** solution operates, the purpose of each file, the exact schemas and data structures returned in the output, the underlying algorithms and extraction techniques, and the technical boundaries of the application.

---

## 1. Executive Summary & Core Tenets

The system is designed to autonomously audit any website or business entity without prior knowledge or pre-configured rules. It operates under four non-negotiable principles:
1. **Zero Paid Services**: Operates without commercial APIs (no OpenAI, Groq, SEMrush, Ahrefs, paid proxies, or scraping subscriptions).
2. **Evidence Grounding**: Every audit finding and Q&A answer is backed by verifiable text from the page's actual HTML markup, HTTP response headers, or network timings.
3. **Multi-Page Autonomous Discovery**: Crawls websites organically using XML sitemaps, `robots.txt`, and internal hyperlinks.
4. **Deterministic Accuracy**: Employs rule-based normalizers, NLP suffix-stemming, and Okapi BM25 probabilistic retrieval to eliminate hallucinations.

---

## 2. File-by-File Breakdown

Below is a breakdown of every file in the codebase and its precise responsibilities:

### Core Package (`seo_audit_agent/`)

#### 1. [`seo_audit_agent/cli.py`](file:///c:/Users/Abhishek%20%20Reddy%20.%20C/Downloads/seo_audit_agent_solution/seo_audit_agent/seo_audit_agent/cli.py)
* **Purpose**: The main command-line entry point and routing layer.
* **Responsibilities**:
  - Defines the CLI argument parser using Python's standard `argparse`.
  - Exposes three strictly independent subcommands (`q1`, `q2`, `q3`) to adhere to the independent evaluation criteria.
  - Automatically creates destination directories for output JSON deliverables.
  - Handles command-line arguments: `--output` (`-o`), `--max-pages`, `--timeout`, and `--concurrency`.
  - Logs progress messages to `sys.stderr` so that only clean, parseable JSON is written to `sys.stdout` (allowing piping like `python -m seo_audit_agent.cli q1 ... | jq`).

#### 2. [`seo_audit_agent/crawler.py`](file:///c:/Users/Abhishek%20%20Reddy%20.%20C/Downloads/seo_audit_agent_solution/seo_audit_agent/seo_audit_agent/crawler.py)
* **Purpose**: The shared crawling and HTTP engine used across all three agents.
* **Key Components**:
  - `Page` (dataclass): Encapsulates a fetched web page (`url`, `status`, `content_type`, `html`, `final_url`, `error`, `headers`, `response_time`, `referrers`).
  - `normalize_url(url, base)`: Resolves relative URLs, removes fragments (`#section`), standardizes lowercase hostnames, and strips default ports (`:80`, `:443`).
  - `same_site(url, root)`: Ensures the crawler stays strictly within the domain boundary, treating `www.` and non-`www` as the same site.
  - `is_crawlable_link(url)`: Filters out binary assets (`.pdf`, `.jpg`, `.zip`, `.mp4`, `.css`, `.js`, etc.) to prevent wasteful downloads.
  - `url_priority_score(url)`: Prioritization heuristic that pushes contact, about, location, legal, and root pages to the front of the crawl queue.
  - `load_robots(session, root)`: Parses the target's `robots.txt` using Python's `urllib.robotparser.RobotFileParser` to respect crawl permissions.
  - `extract_sitemaps(session, root)` & `sitemap_urls(...)`: Discovers sitemaps via `robots.txt` directives and standard `/sitemap.xml` paths, parsing both standard URL sets and recursive sitemap index files.
  - `SiteCrawler`: Multi-threaded crawling engine with a bounded `ThreadPoolExecutor` (default 5 workers), rate-limiting delays, and thread-safe internal link graph tracking to record which pages link to broken URLs.

#### 3. [`seo_audit_agent/q1_onpage.py`](file:///c:/Users/Abhishek%20%20Reddy%20.%20C/Downloads/seo_audit_agent_solution/seo_audit_agent/seo_audit_agent/q1_onpage.py)
* **Purpose**: Implements Question 1: On-page SEO Auditor.
* **Responsibilities**:
  - Evaluates HTML markup and HTTP response headers for 20+ distinct on-page and technical SEO checks.
  - Generates page-level findings backed by verbatim markup quotes and actionable fixes.
  - Runs cross-page sitewide aggregation to detect cannibalizing duplicate `<title>` tags and duplicate `<meta name="description">` tags.
  - Attaches referring URL evidence to HTTP 404/500 errors to highlight the exact page containing the broken link.
  - Writes results to `audit.json`.

#### 4. [`seo_audit_agent/nap.py`](file:///c:/Users/Abhishek%20%20Reddy%20.%20C/Downloads/seo_audit_agent_solution/seo_audit_agent/seo_audit_agent/nap.py)
* **Purpose**: Implements Question 2: Business NAP Consistency Checker.
* **Responsibilities**:
  - Discovers pages containing business Name, Address, and Phone mentions.
  - Extracts candidate signals from 7 distinct sources: JSON-LD structured data, HTML Microdata (`itemprop`), semantic HTML5 `<address>`, clickable `tel:` links, header home branding, logo image alt text, and footer regex patterns.
  - Applies normalizers:
    - `norm_phone`: Strips formatting, handles North American 10/11-digit rules, and normalizes international digits.
    - `norm_address`: Expands abbreviations (`street` &rarr; `st`, `suite` &rarr; `ste`, `avenue` &rarr; `ave`), strips punctuation, and standardizes spacing.
    - `norm_name`: Strips corporate entity suffixes (`Inc`, `LLC`, `Ltd`, `Co`) and punctuation.
  - Compares normalized values across pages to separate cosmetic formatting differences from true data mismatches.
  - Calculates confidence and provides an explicit `confidence_explanation`.
  - Writes results to `nap_report.json`.

#### 5. [`seo_audit_agent/q3_grounded_qa.py`](file:///c:/Users/Abhishek%20%20Reddy%20.%20C/Downloads/seo_audit_agent_solution/seo_audit_agent/seo_audit_agent/q3_grounded_qa.py)
* **Purpose**: Implements Question 3: Grounded Exact-Passage Q&A Agent.
* **Responsibilities**:
  - Extracts verbatim candidate passages from HTML (leaf blocks, semantic tags, and composite `Heading: Content` FAQ structures).
  - Preprocesses query and passages using `simple_stem` (a pure-Python rule-based suffix stemmer) and comprehensive stopword filtering.
  - Evaluates passage relevance using the Okapi BM25 probabilistic model combined with exact multi-word phrase bonuses.
  - Enforces strict grounding thresholds: if term coverage is below 50% or BM25 score is below the confidence limit, it refuses to guess and returns `null` for URL and excerpt.
  - Writes results to `answer.json`.

---

### Test Suite (`tests/`)

* **[`tests/test_crawler.py`](file:///c:/Users/Abhishek%20%20Reddy%20.%20C/Downloads/seo_audit_agent_solution/seo_audit_agent/tests/test_crawler.py)**: Validates URL normalization, fragment stripping, same-site domain validation, binary file extension filtering, and priority scoring.
* **[`tests/test_q1_onpage.py`](file:///c:/Users/Abhishek%20%20Reddy%20.%20C/Downloads/seo_audit_agent_solution/seo_audit_agent/tests/test_q1_onpage.py)**: Feeds synthetic HTML documents with deliberately injected defects (missing titles, empty descriptions, robots noindex, missing alt text, duplicate titles) and verifies exact detection.
* **[`tests/test_nap.py`](file:///c:/Users/Abhishek%20%20Reddy%20.%20C/Downloads/seo_audit_agent_solution/seo_audit_agent/tests/test_nap.py)**: Tests phone, address, and name normalization against varied punctuation, verifies cross-page consensus matching, and confirms mismatch flagging.
* **[`tests/test_q3_grounded_qa.py`](file:///c:/Users/Abhishek%20%20Reddy%20.%20C/Downloads/seo_audit_agent_solution/seo_audit_agent/tests/test_q3_grounded_qa.py)**: Tests suffix stemmer invariance, query token extraction, composite FAQ parsing, BM25 scoring ranking, and refusal to guess on out-of-domain queries.

---

### Demonstration Deliverables (`demo_outputs/`)

* **[`demo_outputs/audit.json`](file:///c:/Users/Abhishek%20%20Reddy%20.%20C/Downloads/seo_audit_agent_solution/seo_audit_agent/demo_outputs/audit.json)**: Real output generated against live site `https://books.toscrape.com/`.
* **[`demo_outputs/nap_report.json`](file:///c:/Users/Abhishek%20%20Reddy%20.%20C/Downloads/seo_audit_agent_solution/seo_audit_agent/demo_outputs/nap_report.json)**: Real NAP report extracted across 25 live pages.
* **[`demo_outputs/answer.json`](file:///c:/Users/Abhishek%20%20Reddy%20.%20C/Downloads/seo_audit_agent_solution/seo_audit_agent/demo_outputs/answer.json)**: Exact passage answer extracted for a user query.

---

## 3. CLI Endpoints & How They Are Invoked

The CLI is structured into three independent subcommands:

| Subcommand | Input Arguments | Optional Flags | Output File | Description |
| :--- | :--- | :--- | :--- | :--- |
| `q1` | `<url>` | `-o`, `--max-pages`, `--timeout`, `--concurrency` | `audit.json` | Runs full on-page SEO crawl and audit |
| `q2` | `<url>` | `-o`, `--max-pages`, `--timeout`, `--concurrency` | `nap_report.json` | Runs business NAP consistency checker |
| `q3` | `<url>`, `"<query>"` | `-o`, `--max-pages`, `--timeout`, `--concurrency` | `answer.json` | Runs grounded exact-passage Q&A agent |

### Execution Commands:
```bash
# Question 1
python -m seo_audit_agent.cli q1 https://example.com -o audit.json --max-pages 150 --concurrency 5

# Question 2
python -m seo_audit_agent.cli q2 https://example.com -o nap_report.json --max-pages 150 --concurrency 5

# Question 3
python -m seo_audit_agent.cli q3 https://example.com "What is your return policy?" -o answer.json --max-pages 150
```

---

## 4. Detailed Data Contracts: What We Return & What We Do

### Question 1: On-Page Auditor (`audit.json`)

#### Output Schema
An array of finding objects:
```typescript
interface AuditFinding {
  metric: string;        // Specific SEO check identifier
  page: string;          // Full URL of the affected page
  severity: "critical" | "high" | "medium" | "low";
  evidence: string;      // Verbatim markup snippet, count, or server response
  suggested_fix: string; // Actionable technical remediation guidance
}
```

#### Metrics Evaluated
1. `http_error`: Page returned 4xx/5xx or timed out. Evidence includes referring page URL.
2. `slow_server_response`: Server response time > 2.5s.
3. `x_robots_noindex`: HTTP response header `X-Robots-Tag: noindex`.
4. `html_lang_missing`: The `<html>` root element lacks a `lang` attribute.
5. `charset_missing`: Missing `<meta charset="...">` declaration.
6. `title_missing`: No `<title>` element in `<head>`.
7. `title_empty`: `<title>` tag is present but contains only whitespace.
8. `title_too_short`: `<title>` is under 15 characters.
9. `title_too_long`: `<title>` exceeds 60 characters.
10. `multiple_titles`: More than one `<title>` element found on a single page.
11. `duplicate_title`: Exact same title used on multiple distinct URLs across the site.
12. `meta_description_missing`: No `<meta name="description">` element found.
13. `meta_description_empty`: Description tag exists but content attribute is blank.
14. `meta_description_too_short`: Description is under 50 characters.
15. `meta_description_too_long`: Description exceeds 160 characters.
16. `multiple_meta_descriptions`: Multiple description tags found on a single page.
17. `duplicate_meta_description`: Exact same description repeated across multiple URLs.
18. `h1_missing`: No `<h1>` heading on page.
19. `multiple_h1`: Multiple `<h1>` headings present.
20. `empty_h1`: `<h1>` tag has no visible text.
21. `heading_hierarchy_skip`: Heading levels skipped (e.g. `<h3>` without an `<h2>`).
22. `robots_noindex`: `<meta name="robots">` contains the `noindex` directive.
23. `robots_nofollow`: `<meta name="robots">` contains the `nofollow` directive.
24. `canonical_missing`: No `<link rel="canonical">` element in `<head>`.
25. `multiple_canonicals`: Multiple canonical tags found on one page.
26. `canonical_empty`: Canonical tag exists with empty href.
27. `canonical_relative`: Canonical URL is relative rather than absolute.
28. `viewport_missing`: No `<meta name="viewport">` found.
29. `viewport_restrictive`: Viewport specifies `user-scalable=no` or `maximum-scale=1.0`.
30. `image_alt_missing`: Images missing the `alt` attribute.
31. `javascript_link`: Navigation links using `href="javascript:..."`.
32. `empty_href_links`: Links with `href="#"` or `href=""`.
33. `mixed_content_link`: Insecure `http://` links referenced on an `https://` page.
34. `thin_content_signal`: Extracted visible content has fewer than 120 words.
35. `open_graph_title_missing`: Missing `<meta property="og:title">`.
36. `open_graph_image_missing`: Missing `<meta property="og:image">`.
37. `structured_data_missing`: Homepage lacks JSON-LD or Microdata structured data.
38. `hreflang_non_absolute`: `hreflang` alternate links pointing to non-absolute URLs.

---

### Question 2: Business NAP Consistency Checker (`nap_report.json`)

#### Output Schema
An array of field report objects (one each for `name`, `address`, `phone`):
```typescript
interface ValueEntry {
  value: string;         // Original verbatim string as extracted from markup
  normalized: string;    // Normalized string used for equivalence comparison
  pages: string[];       // URLs where this specific variation was found
  occurrences: number;   // Total count of occurrences
  sources: string[];     // Sources where found (e.g., ["jsonld", "tel_link", "header_brand"])
}

interface NAPFieldReport {
  field: "name" | "address" | "phone";
  pages_compared: string[];       // All unique URLs where this field was detected
  values: ValueEntry[];           // Distinct observed variations grouped by normalized value
  normalized_values: string[];    // Array of unique normalized values
  confidence: number;             // Quantitative score between 0.00 and 0.99
  confidence_explanation: string; // Detailed natural language reasoning for the confidence score
  verdict: "consistent" | "mismatch" | "not_found";
}
```

#### How NAP Consistency is Determined
1. **Multi-Source Extraction**:
   - `jsonld`: Schema.org `LocalBusiness`, `Organization`, `PostalAddress` JSON-LD blocks.
   - `microdata`: Semantic attributes (`itemprop="name"`, `telephone`, `address`).
   - `html_address`: Dedicated HTML5 `<address>` tags.
   - `tel_link`: Links with `href="tel:..."`.
   - `header_brand`: Root/index links inside `<header>` or `<nav>` containers.
   - `logo_alt`: Logo image `alt` attributes.
   - `footer_text` / `footer_address`: Regex pattern matching in footer containers.
   - `footer_copyright`: Legal entity names extracted from `© [Year] [Company]` notices.
2. **Normalization Logic**:
   - **Phone**: Punctuation and whitespace are removed. 11-digit US/Canada numbers starting with `1` are normalized to 10 digits (`+1 (555) 019-2834` &rarr; `5550192834`).
   - **Address**: Expanded abbreviation table converts `street` &rarr; `st`, `suite` &rarr; `ste`, `boulevard` &rarr; `blvd`, `north` &rarr; `n`. Punctuation is stripped.
   - **Name**: Corporate suffixes (`Inc`, `LLC`, `Ltd`, `Corp`) are removed.
3. **Verdict Assignment**:
   - If 0 instances are found: `verdict = "not_found"`, `confidence = 0.0`.
   - If exactly 1 normalized value exists across all pages: `verdict = "consistent"`.
   - If 2 or more conflicting normalized values exist: `verdict = "mismatch"`.
4. **Confidence Explanation**:
   - Formulates a message stating the number of pages evaluated, the number of independent sources verifying the data, and whether discrepancies were cosmetic or substantial.

---

### Question 3: Grounded Exact-Passage Q&A Agent (`answer.json`)

#### Output Schema
A JSON object containing the query, the source page URL, and the verbatim excerpt:
```typescript
interface AnswerDeliverable {
  query: string;         // The input search query
  url: string | null;    // URL where the passage was found, or null if unsupported
  excerpt: string | null;// Exact, unaltered passage from page markup, or null
}
```

#### How Grounded Exact Passages Are Retrieved
1. **Passage Extraction**:
   - Discrete semantic blocks: `<p>`, `<li>`, `<dd>`, `<blockquote>`, `<td>`.
   - Composite FAQ blocks: Finds `<h1>`-`<h6>` and `<dt>` headings and pairs them with their immediately following paragraph or list (`Heading: Answer`).
   - Leaf containers: Extracts alert boxes, callouts, and notice divs (`<div class="alert...">`) that contain no nested blocks.
2. **Stemming & Tokenization**:
   - Extracts alphanumeric terms.
   - Filters out an extensive stopword dictionary (question words, prepositions, auxiliary verbs).
   - Applies `simple_stem` to match inflections (e.g. `policies` &rarr; `polici`, `returns` &rarr; `return`, `pricing` &rarr; `pric`).
3. **Okapi BM25 Ranking**:
   - Calculates Term Frequency (TF) normalized by passage length against average document length.
   - Computes Inverse Document Frequency (IDF) based on term frequency across the site's passage corpus.
   - Adds an exact multi-word phrase bonus (+3.0) when contiguous query words appear verbatim in the passage.
4. **Refusal to Guess**:
   - Calculates query term coverage (fraction of non-stopword query keywords present in the passage).
   - Requires at least 50% term coverage (or 100% for single-keyword queries) AND a minimum BM25 threshold of 1.8.
   - If no passage satisfies both criteria, the agent returns `url: null` and `excerpt: null`. It never paraphrases or invents answers.

---

## 5. Technical Scope & Boundaries

### What the Application Handles:
* **Protocol & Standards**: Full HTTP/1.1 and HTTP/2 compliance over standard HTTP and HTTPS.
* **Concurrency**: Thread-pool concurrent crawling (configurable 1–10 workers) with polite inter-request pacing.
* **Site Size**: Handles small to mid-sized sites (default 150 pages, configurable up to 500+).
* **Error Resilience**: Handles connection drops, SSL errors, timeouts, redirect loops, and malformed HTML gracefully without crashing.
* **Markup Styles**: Parses HTML5, XHTML, JSON-LD, Microdata, Open Graph, and XML sitemaps.

### Known Boundaries & Limitations:
* **Client-Side JavaScript Rendering**: The crawler analyzes the server-returned HTML response. If a site's primary content is rendered purely via client-side JavaScript execution (e.g., single-page applications without Server-Side Rendering), elements generated exclusively by client-side JS runtime are not in the raw HTML payload.
* **Captchas & Cloudflare Challenges**: In accordance with the assignment's "no paid services or proxy services" constraint, pages behind Cloudflare Turnstile or anti-bot challenge screens will return standard HTTP 403/503 responses, which are flagged as HTTP errors in `audit.json`.
