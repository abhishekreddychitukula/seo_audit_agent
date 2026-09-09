# Strategic Roadmap: Enhancements, Advanced NAP Discovery & AI Integration

This document outlines an engineering roadmap for advancing the **SEO Audit Agent** from its current free, rule-based foundation into an enterprise-grade, AI-augmented auditing and Answer Engine Optimization (AEO) platform.

---

## 1. Expanding High-Impact SEO & AEO Metrics

While the current engine checks 20+ core on-page signals, search engines and AI answer engines (Perplexity, Google AI Overviews, SearchGPT) evaluate deeper structural, architectural, and semantic factors.

### A. Technical Architecture & Crawl Efficiency
1. **Click-Depth Analysis**:
   - *Impact*: Pages more than 3 clicks away from the homepage suffer from poor crawl frequency and weak PageRank distribution.
   - *Implementation*: Track shortest path length in the crawler’s breadth-first link graph from the root URL.
2. **Redirect Chains & Loops**:
   - *Impact*: Chains of 301/302 redirects waste crawl budget and dilute link equity.
   - *Implementation*: Inspect `requests.Response.history` to record the entire hop sequence (e.g., `http://site.com` &rarr; `https://site.com` &rarr; `https://site.com/` &rarr; `https://site.com/en/`).
3. **Orphan Page Detection**:
   - *Impact*: URLs present in the XML sitemap but never linked internally from any crawlable HTML page.
   - *Implementation*: Compare `sitemap_urls` against the set of crawled URLs discovered via `<a href="...">`.
4. **Faceted Navigation & URL Parameter Bloat**:
   - *Impact*: E-commerce filters (`?sort=price&color=blue&size=m`) create near-infinite duplicate pages that deplete crawl budgets.
   - *Implementation*: Detect URL query-string parameter explosion and check for `rel="canonical"` consolidation or `robots.txt` parameter disallows.

### B. Answer Engine Optimization (AEO) & LLM Readiness
1. **`llms.txt` and `llms-full.txt` Audit**:
   - *Impact*: Emerging standard for providing clean markdown content directly to AI agents and web LLMs.
   - *Implementation*: Check if `https://domain.com/llms.txt` exists, returns HTTP 200, and lists high-value documentation paths.
2. **AI Crawler Permissions in `robots.txt`**:
   - *Impact*: Accidental disallow rules blocking AI crawlers (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`).
   - *Implementation*: Parse `robots.txt` specifically for AI user agents and report whether the site is visible to LLM retrieval systems.
3. **Schema.org Rich Entity Density**:
   - *Impact*: Essential for SERP rich cards and knowledge graph inclusion.
   - *Expansion*: Beyond `LocalBusiness` and `Organization`, audit for `FAQPage`, `HowTo`, `Product` (with `offers` and `aggregateRating`), `BreadcrumbList`, and `Article`.
4. **Direct Answer Block Formatting**:
   - *Impact*: Search engines favor concise definition blocks (40–60 words) immediately following target question headings for featured snippets.
   - *Implementation*: Measure whether `<h2>`/`<h3>` question headings are immediately followed by a direct answer sentence or by conversational filler.

### C. Performance & Core Web Vitals (Static Heuristics)
1. **DOM Depth & Node Count**:
   - *Impact*: Massive DOMs (>1,500 nodes or depth >32) degrade browser rendering and Core Web Vitals (Interaction to Next Paint - INP).
   - *Implementation*: Count total BeautifulSoup tags and compute maximum tree depth.
2. **Render-Blocking CSS/JS in `<head>`**:
   - *Impact*: Slows First Contentful Paint (FCP).
   - *Implementation*: Flag `<link rel="stylesheet">` without media queries and `<script src="...">` tags lacking `async` or `defer` attributes inside `<head>`.
3. **Modern Image Formats & Dimensions**:
   - *Impact*: Uncompressed PNG/JPEG without explicit `width` and `height` causes Cumulative Layout Shift (CLS).
   - *Implementation*: Check for WebP/AVIF format adoption and presence of layout dimension attributes on `<img>` tags.

---

## 2. Advanced Business NAP Discovery & Consistency

A major challenge in local SEO is accurately auditing business Name, Address, and Phone numbers (NAP) across complex, multi-page, or multi-location websites.

### A. Intelligent Page Discovery for Business Mentions
Currently, the crawler prioritizes `/contact` and `/about`. To ensure complete coverage across all pages mentioning the business:
1. **URL Semantic Pattern Scoring**:
   ```python
   HIGH_VALUE_PATTERNS = [
       r"/contact", r"/about", r"/locations?", r"/stores?", r"/find-a-store",
       r"/branches", r"/our-offices", r"/imprint", r"/impressum",
       r"/terms", r"/privacy", r"/legal", r"/help", r"/support"
   ]
   ```
2. **Footer Template Deconstruction**:
   - Footers appear across 90%+ of website pages.
   - By identifying the `<footer>` container or DOM subtree shared across page templates, the agent can verify if the global NAP block is consistent across all sections (e.g. blog vs shop vs landing pages).
3. **Internal Site Search Querying**:
   - When available, query the site's internal search endpoint (e.g. `https://site.com/search?q=contact` or `?q=headquarters`) to uncover buried location pages.

### B. Multi-Location Business & Franchise Handling
Many businesses operate multiple physical stores (e.g. an Austin branch and a Dallas branch). A naive consistency checker flags different addresses as a "mismatch".
* **Proposed Enhancement**:
  - Group extracted addresses by branch/store identifiers (e.g. "Austin Office", "Dallas Showroom").
  - Evaluate consistency **per branch location** rather than forcing a single global address across the entire company.
  - Detect whether the site uses `Store`, `Restaurant`, or `LocalBusiness` arrays in JSON-LD.

### C. Postal & Telephone Standardization (Zero-Cost / Open-Source)
1. **Google's `libphonenumber` (via Python `phonenumbers`)**:
   - Free, open-source library used by Android.
   - Parses international phone formats, detects carrier validity, normalizes to E.164 (`+15551234567`), international (`+1 555-123-4567`), or national (`(555) 123-4567`), eliminating false-positive formatting flags.
2. **Geocoding & Postal Address Verification (OpenStreetMap / Nominatim)**:
   - Free, open-source geocoding API.
   - Resolves raw text into standardized postal addresses, verifying street name, postal code, state, and geographic coordinates without paid Google Maps APIs.

```
   Raw Markup (JSON-LD, Footer, Address tags)
                      │
                      ▼
   ┌─────────────────────────────────────┐
   │ Extraction Engine                   │
   │ (JSON-LD, Microdata, Tel, RegEx)    │
   └──────────────────┬──────────────────┘
                      │
                      ▼
   ┌─────────────────────────────────────┐
   │ Open-Source Normalization           │
   │ - phonenumbers (E.164 format)       │
   │ - USPS / Address Standardizer       │
   │ - Corporate Suffix Stripper         │
   └──────────────────┬──────────────────┘
                      │
                      ▼
   ┌─────────────────────────────────────┐
   │ Cluster & Consistency Engine        │
   │ - Single-Location Consensus         │
   │ - Multi-Branch Grouping             │
   │ - Confidence Reasoning Formulator   │
   └─────────────────────────────────────┘
```

---

## 3. Integrating AI into the Application (100% Free & Open)

In accordance with the assignment constraint (*"No paid API subscriptions; free tier or local LLMs permitted"*), AI can be integrated using **free-tier APIs** (Google Gemini free tier, Groq free tier) or **local open-source SLMs/LLMs** (Ollama, Hugging Face Transformers, ONNX Runtime).

```mermaid
flowchart TD
    RawHTML[Crawled HTML & Markup] --> Extractor[Parser & Feature Extractor]
    Extractor --> RuleEngine[Rule-Based Auditing Engine]
    Extractor --> LocalEmbeddings[Local Vector Embeddings (BGE-small / MiniLM)]
    
    RuleEngine --> Q1Findings[Raw Audit Findings]
    Q1Findings --> LocalLLM[Local SLM / Free-Tier LLM (Llama-3-8B / Gemini Flash)]
    LocalLLM --> ActionableCode[Ready-to-Deploy Code Fixes & Explanations]
    
    LocalEmbeddings --> HybridSearch[Hybrid BM25 + Dense Vector Search]
    HybridSearch --> CrossEncoder[Local Cross-Encoder Reranker]
    CrossEncoder --> ExactPassage[Grounded Verbatim Answer]
```

### A. AI for Question 1: Automated Code-Fix Generation
* **Current Limitation**: Fix suggestions are static text templates (e.g. *"Add a unique meta description"*).
* **AI Integration**:
  - Pass the page's visible text and detected defects to a local SLM (e.g., `Llama-3-8B` via Ollama or `Gemini 1.5 Flash` free tier).
  - The model generates **exact, copy-paste HTML markup**:
    - Generates a compelling 150-character meta description based on the page's specific content.
    - Generates complete, valid Schema.org JSON-LD tailored to the page type.
    - Restructures heading outlines (`h1` &rarr; `h2` &rarr; `h3`) while preserving the text.

### B. AI for Question 2: Named Entity Recognition (NER) & Ambiguity Resolution
* **Current Limitation**: Regex pattern matching can miss unconventional address layouts or extract navigational false positives.
* **AI Integration**:
  - Use lightweight, open-source Named Entity Recognition (such as `spaCy` `en_core_web_sm` or `GLiNER`):
    - Identifies `ORG` (Business Name), `GPE`/`LOC` (Address components), and `PHONE` directly from unstructured body text.
  - Zero-shot LLM consistency reasoning:
    - Prompt: *"Compare these two address strings found on different pages. Determine if they represent the same physical location with abbreviation differences, different branches of the same company, or an error."*

### C. AI for Question 3: Hybrid Retrieval (BM25 + Dense Embeddings + Reranker)
* **Current Limitation**: Pure BM25 relies on exact or stemmed lexical overlap. It struggles with semantic synonyms (e.g. *"cost of shipping"* vs *"delivery fees"*).
* **AI Integration**:
  1. **Dense Vector Embeddings (Zero Cost, Runs Locally)**:
     - Run a tiny, fast embedding model like `sentence-transformers/all-MiniLM-L6-v2` or `BAAI/bge-small-en-v1.5` via ONNX or PyTorch.
     - Generates 384-dimensional embeddings for all extracted page passages in seconds.
  2. **Hybrid Search with Reciprocal Rank Fusion (RRF)**:
     - Combine BM25 lexical score with Dense Vector cosine similarity:
       $$RRF(d) = \frac{1}{60 + \text{rank}_{\text{BM25}}(d)} + \frac{1}{60 + \text{rank}_{\text{Dense}}(d)}$$
     - Bridges the gap between exact keyword matches and conceptual synonym search.
  3. **Local Cross-Encoder Reranking**:
     - Pass the top 5 candidates to a local cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
     - Scores exact passage suitability and enforces a strict confidence cutoff for zero hallucination.

---

## 4. Architectural Implementation Blueprint

### Step 1: Optional Local AI Enhancement Layer (`ai_engine.py`)
Add a modular AI helper that activates only if an Ollama instance or free API key is detected, gracefully falling back to pure algorithmic mode:

```python
# Conceptual module: seo_audit_agent/ai_engine.py
import os
import requests

OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")

def query_local_llm(prompt: str, model: str = "llama3:8b") -> str | None:
    try:
        res = requests.post(
            OLLAMA_ENDPOINT,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=10.0
        )
        if res.ok:
            return res.json().get("response")
    except Exception:
        pass
    return None  # Fallback gracefully to rule-based logic
```

### Step 2: Automated Fix Generator for Q1
```python
def generate_ai_suggested_fix(page_title: str, body_text: str, finding_type: str) -> str:
    prompt = f"""
    The following webpage has an SEO issue: '{finding_type}'.
    Page title: {page_title}
    Page snippet: {body_text[:500]}
    
    Write an optimal, production-ready HTML code snippet to fix this issue.
    Keep explanations under 2 sentences.
    """
    ai_fix = query_local_llm(prompt)
    return ai_fix or "Default rule-based remediation guidance."
```

### Step 3: Upgrading Grounded Q&A with Dense Embeddings
```python
# Embeddings via open-source sentence-transformers (offline, CPU-friendly)
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

def semantic_rank(query: str, passages: list[str]) -> list[float]:
    q_vec = model.encode(query)
    p_vecs = model.encode(passages)
    similarities = np.dot(p_vecs, q_vec) / (np.linalg.norm(p_vecs, axis=1) * np.linalg.norm(q_vec))
    return similarities.tolist()
```

---

## 5. Summary of Recommended Roadmap Phases

| Phase | Milestone | Expected Impact | Key Technologies |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Expanded Technical Metrics** | Catch deep architecture issues (chains, orphans, click depth) | Python link-graph traversal, HTTP hop inspect |
| **Phase 2** | **AEO & LLM Readiness Audits** | Prepare sites for AI search engines (Perplexity, SearchGPT) | `llms.txt` checks, AI robots permissions, Schema.org |
| **Phase 3** | **Open-Source Phone & Postal Libs** | 100% precision in international phone & street standardization | `phonenumbers`, OpenStreetMap Nominatim |
| **Phase 4** | **Hybrid Search for Q3** | Natural language queries matching conceptual synonyms | `all-MiniLM-L6-v2`, BM25 + Dense RRF |
| **Phase 5** | **Local SLM Fix Generation** | Automated, production-ready code generation for Q1 fixes | `Ollama` / `Llama-3-8B` / `Gemini Free Tier` |
