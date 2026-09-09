from __future__ import annotations

import json
import re
from collections import defaultdict
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

from .ai_provider import AIProvider, ProviderType
from .crawler import Page, SiteCrawler


def finding(metric: str, page: str, severity: str, evidence: str, suggested_fix: str) -> dict:
    return {
        "metric": metric,
        "page": page,
        "severity": severity,
        "evidence": evidence,
        "suggested_fix": suggested_fix,
    }


def visible_text(soup: BeautifulSoup) -> str:
    for x in soup(["script", "style", "noscript", "template", "svg"]):
        x.decompose()
    return " ".join(soup.stripped_strings)


def compute_max_dom_depth(node: Tag, current_depth: int = 1) -> int:
    max_d = current_depth
    for child in node.find_all(recursive=False):
        if isinstance(child, Tag):
            max_d = max(max_d, compute_max_dom_depth(child, current_depth + 1))
    return max_d


def audit(
    pages: list[Page],
    crawler: SiteCrawler | None = None,
    ai: AIProvider | None = None,
) -> list[dict]:
    findings: list[dict] = []
    title_pages: dict[str, list[str]] = defaultdict(list)
    desc_pages: dict[str, list[str]] = defaultdict(list)
    canonical_targets: dict[str, list[str]] = defaultdict(list)

    root_page = pages[0] if pages else None
    root_url = crawler.root_url if crawler else (root_page.final_url if root_page else "")
    root_netloc = urlparse(root_url).netloc if root_url else ""
    root_scheme = urlparse(root_url).scheme if root_url else "https"

    # Global Site-Level Checks (llms.txt & AI Crawler Permissions)
    if root_url and crawler:
        # Check /llms.txt
        llms_url = f"{root_scheme}://{root_netloc}/llms.txt"
        try:
            r_llms = crawler.session.get(llms_url, timeout=6.0)
            if not r_llms.ok or len(r_llms.text.strip()) < 10:
                findings.append(finding(
                    metric="llms_txt_missing",
                    page=llms_url,
                    severity="low",
                    evidence=f"No active /llms.txt found (HTTP status {r_llms.status_code if hasattr(r_llms, 'status_code') else 'error'}).",
                    suggested_fix="Create an /llms.txt file to help AI search engines (Perplexity, SearchGPT, Gemini) index site knowledge.",
                ))
        except Exception:
            pass

        # Check robots.txt for AI bots
        rp_text = getattr(crawler.robots, "default_useragent", "") or ""
        try:
            rp_res = crawler.session.get(f"{root_scheme}://{root_netloc}/robots.txt", timeout=6.0)
            if rp_res.ok:
                txt = rp_res.text
                blocked_bots = []
                for bot in ("GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "CCBot"):
                    if re.search(rf"User-agent:\s*{bot}\b.*?Disallow:\s*/\s*(?:\n|$)", txt, re.I | re.DOTALL):
                        blocked_bots.append(bot)
                if blocked_bots:
                    findings.append(finding(
                        metric="ai_crawler_blocked",
                        page=f"{root_scheme}://{root_netloc}/robots.txt",
                        severity="medium",
                        evidence=f"robots.txt explicitly blocks AI search crawlers: {', '.join(blocked_bots)}.",
                        suggested_fix="Review robots.txt rules if visibility in AI answer engines (SearchGPT, Claude, Gemini) is desired.",
                    ))
        except Exception:
            pass

    # Page-by-Page Audit
    for p in pages:
        # Check click depth
        if p.depth > 3:
            findings.append(finding(
                metric="click_depth_high",
                page=p.final_url,
                severity="low",
                evidence=f"Page is at click depth {p.depth} from homepage (recommended max is 3).",
                suggested_fix="Improve internal linking hierarchy so important pages are accessible within 3 clicks of the root.",
            ))

        # Check redirect chains
        if len(p.redirect_chain) > 1:
            chain_str = " -> ".join(f"{h['status']} {h['url']}" for h in p.redirect_chain)
            findings.append(finding(
                metric="redirect_chain",
                page=p.url,
                severity="medium",
                evidence=f"URL required {len(p.redirect_chain)} redirect hops: {chain_str}.",
                suggested_fix="Update internal links to point directly to the destination URL to preserve crawl budget and link equity.",
            ))

        # Check orphan pages in sitemap
        if crawler and p.url in crawler.sitemap_discovered_urls and p.depth > 0 and len(p.referrers) == 0:
            findings.append(finding(
                metric="orphan_page_in_sitemap",
                page=p.final_url,
                severity="medium",
                evidence="URL was discovered in sitemap.xml but has zero internal links pointing to it from crawled pages.",
                suggested_fix="Add internal contextual links to this page so users and search bots can discover it naturally.",
            ))

        # 1. HTTP Status & Network Errors
        if not p.html or p.status >= 400 or p.status == 0:
            ref_info = f" Discovered via link on {p.referrers[0]}." if p.referrers else ""
            if p.status == 0:
                msg = f"Connection failed or timed out: {p.error or 'network error'}.{ref_info}"
            else:
                msg = f"HTTP response status is {p.status}.{ref_info}"
            findings.append(finding(
                metric="http_error",
                page=p.url,
                severity="critical" if p.status >= 500 or p.status == 0 else "high",
                evidence=msg,
                suggested_fix="Ensure the page resolves successfully (HTTP 200) or update/remove internal links pointing to it.",
            ))
            continue

        # Page response time check
        if p.response_time > 2.5:
            findings.append(finding(
                metric="slow_server_response",
                page=p.final_url,
                severity="low",
                evidence=f"Server response time was {p.response_time:.2f}s, exceeding recommended 2.5s threshold.",
                suggested_fix="Optimize server-side response times, implement caching, or use a CDN to reduce time to first byte.",
            ))

        # Check HTTP response headers for X-Robots-Tag
        x_robots = p.headers.get("x-robots-tag", "").lower()
        if "noindex" in x_robots:
            findings.append(finding(
                metric="x_robots_noindex",
                page=p.final_url,
                severity="high",
                evidence=f'HTTP response header X-Robots-Tag is "{p.headers.get("x-robots-tag")}".',
                suggested_fix="Remove the noindex directive from the X-Robots-Tag HTTP header if this page should be indexed.",
            ))

        soup = BeautifulSoup(p.html, "html.parser")

        # DOM Size and Depth (INP & Render Performance)
        all_tags = soup.find_all()
        dom_node_count = len(all_tags)
        if dom_node_count > 1500:
            findings.append(finding(
                metric="excessive_dom_size",
                page=p.final_url,
                severity="low",
                evidence=f"Document contains {dom_node_count} DOM elements (recommended maximum is 1,500).",
                suggested_fix="Simplify DOM structure and paginate long lists to improve Interaction to Next Paint (INP).",
            ))

        # Render-Blocking Resources in <head>
        head_tag = soup.find("head")
        if head_tag:
            blocking_scripts = []
            for s in head_tag.find_all("script", src=True):
                if not s.get("async") and not s.get("defer") and s.get("type") != "module":
                    blocking_scripts.append(s["src"][:60])
            if blocking_scripts:
                findings.append(finding(
                    metric="render_blocking_script",
                    page=p.final_url,
                    severity="low",
                    evidence=f"Found {len(blocking_scripts)} parser-blocking script(s) in <head>: {blocking_scripts[:2]!r}.",
                    suggested_fix="Add 'defer' or 'async' attribute to non-critical scripts in <head> to improve First Contentful Paint.",
                ))

        # 2. Language and Encoding
        html_tag = soup.find("html")
        lang = html_tag.get("lang") if html_tag else None
        if not lang:
            findings.append(finding(
                metric="html_lang_missing",
                page=p.final_url,
                severity="low",
                evidence="The root <html> element is missing a 'lang' attribute.",
                suggested_fix='Add a valid BCP-47 language tag to the root element, e.g., <html lang="en">.',
            ))

        charset = soup.find("meta", attrs={"charset": True})
        http_equiv = soup.find("meta", attrs={"http-equiv": re.compile(r"^content-type$", re.I)})
        if not charset and not http_equiv:
            findings.append(finding(
                metric="charset_missing",
                page=p.final_url,
                severity="low",
                evidence="No <meta charset=\"...\"> or http-equiv Content-Type tag was found in <head>.",
                suggested_fix='Specify character encoding early in the document <head>, e.g., <meta charset="utf-8">.',
            ))

        # 3. Title Tag Checks
        title_tags = soup.find_all("title")
        primary_title = ""
        if len(title_tags) == 0:
            findings.append(finding(
                metric="title_missing",
                page=p.final_url,
                severity="high",
                evidence="No <title> tag found in the document.",
                suggested_fix="Add a unique, descriptive <title> element inside the <head> section.",
            ))
        else:
            if len(title_tags) > 1:
                findings.append(finding(
                    metric="multiple_titles",
                    page=p.final_url,
                    severity="medium",
                    evidence=f"Found {len(title_tags)} <title> tags: {[t.get_text(strip=True) for t in title_tags]!r}.",
                    suggested_fix="Keep only a single, authoritative <title> element per page.",
                ))
            primary_title = title_tags[0].get_text(strip=True)
            if not primary_title:
                findings.append(finding(
                    metric="title_empty",
                    page=p.final_url,
                    severity="high",
                    evidence="The <title> element exists but is empty or contains only whitespace.",
                    suggested_fix="Populate the <title> tag with a meaningful description of the page's topic.",
                ))
            else:
                title_pages[primary_title].append(p.final_url)
                if len(primary_title) < 15:
                    findings.append(finding(
                        metric="title_too_short",
                        page=p.final_url,
                        severity="low",
                        evidence=f'Title length is only {len(primary_title)} characters: "{primary_title}".',
                        suggested_fix="Expand the title to between 30 and 60 characters with target keywords and brand identity.",
                    ))
                elif len(primary_title) > 60:
                    findings.append(finding(
                        metric="title_too_long",
                        page=p.final_url,
                        severity="low",
                        evidence=f'Title length is {len(primary_title)} characters (exceeds 60): "{primary_title}".',
                        suggested_fix="Shorten title to under 60 characters to avoid truncation in search engine result pages.",
                    ))

        # 4. Meta Description Checks
        desc_tags = soup.find_all("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if len(desc_tags) == 0:
            findings.append(finding(
                metric="meta_description_missing",
                page=p.final_url,
                severity="medium",
                evidence="No <meta name=\"description\"> tag found on the page.",
                suggested_fix="Add a compelling, unique meta description between 50 and 160 characters summarizing the page.",
            ))
        else:
            if len(desc_tags) > 1:
                findings.append(finding(
                    metric="multiple_meta_descriptions",
                    page=p.final_url,
                    severity="medium",
                    evidence=f"Found {len(desc_tags)} meta description tags.",
                    suggested_fix="Consolidate multiple meta description tags into a single authoritative tag.",
                ))
            desc_text = (desc_tags[0].get("content") or "").strip()
            if not desc_text:
                findings.append(finding(
                    metric="meta_description_empty",
                    page=p.final_url,
                    severity="medium",
                    evidence="The <meta name=\"description\"> tag exists but its content attribute is empty.",
                    suggested_fix="Provide a descriptive summary in the content attribute of the meta description.",
                ))
            else:
                desc_pages[desc_text].append(p.final_url)
                if len(desc_text) < 50:
                    findings.append(finding(
                        metric="meta_description_too_short",
                        page=p.final_url,
                        severity="low",
                        evidence=f'Meta description is only {len(desc_text)} characters: "{desc_text}".',
                        suggested_fix="Expand the meta description to 50-160 characters to provide a rich summary for search snippets.",
                    ))
                elif len(desc_text) > 160:
                    findings.append(finding(
                        metric="meta_description_too_long",
                        page=p.final_url,
                        severity="low",
                        evidence=f"Meta description is {len(desc_text)} characters, exceeding the 160 character limit.",
                        suggested_fix="Trim meta description to under 160 characters to prevent snippet truncation on search results.",
                    ))

        # 5. Heading Structure Checks
        h1_tags = soup.find_all("h1")
        if len(h1_tags) == 0:
            findings.append(finding(
                metric="h1_missing",
                page=p.final_url,
                severity="medium",
                evidence="No <h1> heading tag was found in the page markup.",
                suggested_fix="Add exactly one <h1> element to communicate the primary topic of the page.",
            ))
        elif len(h1_tags) > 1:
            h1_texts = [h.get_text(" ", strip=True) for h in h1_tags]
            findings.append(finding(
                metric="multiple_h1",
                page=p.final_url,
                severity="low",
                evidence=f"Found {len(h1_tags)} <h1> elements: {h1_texts[:4]!r}.",
                suggested_fix="Use a single primary <h1> element for the main title, structuring subtopics with <h2> and <h3>.",
            ))
        else:
            h1_content = h1_tags[0].get_text(" ", strip=True)
            if not h1_content:
                findings.append(finding(
                    metric="empty_h1",
                    page=p.final_url,
                    severity="medium",
                    evidence="The <h1> element contains no visible text.",
                    suggested_fix="Add descriptive heading text inside the <h1> tag.",
                ))

        h2_count = len(soup.find_all("h2"))
        h3_count = len(soup.find_all("h3"))
        if h3_count > 0 and h2_count == 0:
            findings.append(finding(
                metric="heading_hierarchy_skip",
                page=p.final_url,
                severity="low",
                evidence=f"Document contains {h3_count} <h3> elements but no <h2> elements.",
                suggested_fix="Maintain a logical heading hierarchy by nesting <h3> headings under <h2> sections.",
            ))

        # 6. Robots Directives
        robots_meta = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
        if robots_meta:
            rob_content = (robots_meta.get("content") or "").lower()
            if re.search(r"\bnoindex\b", rob_content):
                findings.append(finding(
                    metric="robots_noindex",
                    page=p.final_url,
                    severity="high",
                    evidence=f'<meta name="robots" content="{robots_meta.get("content")}"> contains "noindex".',
                    suggested_fix="Remove 'noindex' if this page is intended to be indexed and ranked by search engines.",
                ))
            if re.search(r"\bnofollow\b", rob_content):
                findings.append(finding(
                    metric="robots_nofollow",
                    page=p.final_url,
                    severity="medium",
                    evidence=f'<meta name="robots" content="{robots_meta.get("content")}"> contains "nofollow".',
                    suggested_fix="Remove 'nofollow' if search crawlers should discover and pass link equity through internal links.",
                ))

        # 7. Canonicalization Checks
        canon_links = soup.find_all("link", attrs={"rel": lambda v: v and "canonical" in (v if isinstance(v, list) else [v])})
        if len(canon_links) == 0:
            findings.append(finding(
                metric="canonical_missing",
                page=p.final_url,
                severity="medium",
                evidence="No <link rel=\"canonical\"> tag found in the document <head>.",
                suggested_fix="Add an explicit canonical link pointing to the preferred authoritative URL.",
            ))
        elif len(canon_links) > 1:
            findings.append(finding(
                metric="multiple_canonicals",
                page=p.final_url,
                severity="high",
                evidence=f"Found {len(canon_links)} conflicting canonical link tags.",
                suggested_fix="Specify only one canonical link element per page to avoid indexing ambiguity.",
            ))
        else:
            canon_href = (canon_links[0].get("href") or "").strip()
            if not canon_href:
                findings.append(finding(
                    metric="canonical_empty",
                    page=p.final_url,
                    severity="medium",
                    evidence='The <link rel="canonical"> tag has an empty href attribute.',
                    suggested_fix="Specify the absolute target URL in the canonical tag's href attribute.",
                ))
            elif not re.match(r"^https?://", canon_href):
                findings.append(finding(
                    metric="canonical_relative",
                    page=p.final_url,
                    severity="low",
                    evidence=f'Canonical href is a relative path "{canon_href}" instead of an absolute URL.',
                    suggested_fix="Use full absolute URLs (including https:// and domain) in canonical links.",
                ))
            else:
                canonical_targets[canon_href].append(p.final_url)

        # 8. Mobile Viewport Checks
        vp = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
        if not vp:
            findings.append(finding(
                metric="viewport_missing",
                page=p.final_url,
                severity="high",
                evidence="No <meta name=\"viewport\"> tag found.",
                suggested_fix='Add <meta name="viewport" content="width=device-width, initial-scale=1.0"> for mobile responsiveness.',
            ))
        else:
            vp_content = (vp.get("content") or "").lower()
            if "user-scalable=no" in vp_content or "maximum-scale=1" in vp_content:
                findings.append(finding(
                    metric="viewport_restrictive",
                    page=p.final_url,
                    severity="low",
                    evidence=f'Viewport disables zoom: content="{vp.get("content")}".',
                    suggested_fix="Avoid restricting user zoom (user-scalable=no) to ensure accessibility standards are met.",
                ))

        # 9. Image Alt & CLS Dimensions
        images = soup.find_all("img")
        missing_alt = []
        missing_dimensions = []
        for img in images:
            src = img.get("src") or img.get("data-src") or "unknown"
            if "alt" not in img.attrs:
                missing_alt.append(src)
            # Layout shift CLS check: image lacking width or height
            if not (img.get("width") and img.get("height")) and not src.lower().endswith(".svg"):
                missing_dimensions.append(src)

        if missing_alt:
            findings.append(finding(
                metric="image_alt_missing",
                page=p.final_url,
                severity="medium",
                evidence=f"{len(missing_alt)} image(s) completely lack an 'alt' attribute. Sample src: {missing_alt[:2]!r}.",
                suggested_fix="Add descriptive alt text to images for search engine image indexing and screen reader accessibility.",
            ))

        if len(missing_dimensions) > 3:
            findings.append(finding(
                metric="image_dimensions_missing",
                page=p.final_url,
                severity="low",
                evidence=f"{len(missing_dimensions)} image(s) lack explicit width/height attributes (Cumulative Layout Shift risk).",
                suggested_fix="Add width and height attributes to <img> elements to reserve layout space and prevent layout shifts.",
            ))

        # 10. Links & Navigation Quality
        is_https_page = p.final_url.lower().startswith("https://")
        mixed_content_links = []
        js_links = []
        empty_links = 0
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            if href.lower().startswith("javascript:"):
                js_links.append(href[:60])
            elif href == "#" or href == "":
                empty_links += 1
            elif is_https_page and href.lower().startswith("http://"):
                mixed_content_links.append(href[:60])

        if js_links:
            findings.append(finding(
                metric="javascript_link",
                page=p.final_url,
                severity="low",
                evidence=f"Found {len(js_links)} navigation link(s) using 'javascript:' protocol: {js_links[:2]!r}.",
                suggested_fix="Replace javascript: pseudo-links with standard crawlable URLs or use button elements.",
            ))

        if empty_links > 3:
            findings.append(finding(
                metric="empty_href_links",
                page=p.final_url,
                severity="low",
                evidence=f"Found {empty_links} anchor elements with empty href or href=\"#\".",
                suggested_fix="Use valid target URLs for navigation links or convert to buttons if triggering actions.",
            ))

        if mixed_content_links:
            findings.append(finding(
                metric="mixed_content_link",
                page=p.final_url,
                severity="low",
                evidence=f"HTTPS page contains {len(mixed_content_links)} insecure HTTP link(s): {mixed_content_links[:2]!r}.",
                suggested_fix="Upgrade insecure http:// URLs to https:// to maintain end-to-end transport security.",
            ))

        # 11. Content Thinness
        text_copy = visible_text(BeautifulSoup(p.html, "html.parser"))
        words = re.findall(r"\b[\w’'-]+\b", text_copy)
        is_root = urlparse(p.final_url).path in {"", "/"}
        if len(words) < 120 and not is_root:
            findings.append(finding(
                metric="thin_content_signal",
                page=p.final_url,
                severity="low",
                evidence=f"Page contains approximately {len(words)} visible words, which may signal thin content to search engines.",
                suggested_fix="Expand the page copy with substantive, original content that satisfies target search intent.",
            ))

        # 12. Open Graph & Social Signals
        og_title = soup.find("meta", attrs={"property": re.compile(r"^og:title$", re.I)})
        if not og_title:
            findings.append(finding(
                metric="open_graph_title_missing",
                page=p.final_url,
                severity="low",
                evidence="No Open Graph <meta property=\"og:title\"> found.",
                suggested_fix="Add an og:title tag to optimize how content appears when shared across social networks.",
            ))

        og_image = soup.find("meta", attrs={"property": re.compile(r"^og:image$", re.I)})
        if not og_image:
            findings.append(finding(
                metric="open_graph_image_missing",
                page=p.final_url,
                severity="low",
                evidence="No Open Graph <meta property=\"og:image\"> found.",
                suggested_fix="Add an og:image tag with an appropriate preview image (1200x630px recommended).",
            ))

        # 13. Structured Data / Schema Markup Check
        has_ldjson = bool(soup.find("script", type=re.compile(r"application/ld\+json", re.I)))
        has_microdata = bool(soup.find(attrs={"itemscope": True}))
        if not has_ldjson and not has_microdata and is_root:
            findings.append(finding(
                metric="structured_data_missing",
                page=p.final_url,
                severity="low",
                evidence="Homepage lacks Schema.org structured data (neither JSON-LD nor Microdata detected).",
                suggested_fix="Implement Schema.org JSON-LD structured data (e.g. Organization, WebSite) for rich snippet eligibility.",
            ))

        # 14. Hreflang Validation
        for link in soup.find_all("link", attrs={"rel": lambda v: v and "alternate" in (v if isinstance(v, list) else [v])}):
            hl = link.get("hreflang")
            href = link.get("href", "")
            if hl and href:
                if not re.match(r"^https?://", href):
                    findings.append(finding(
                        metric="hreflang_non_absolute",
                        page=p.final_url,
                        severity="low",
                        evidence=f'hreflang="{hl}" target is not an absolute URL: "{href}".',
                        suggested_fix="Ensure all hreflang alternate links use fully-qualified absolute URLs.",
                    ))

    # 15. Sitewide Duplicate Title & Meta Description Checks
    for title, urls in title_pages.items():
        if title and len(urls) > 1:
            for u in urls:
                findings.append(finding(
                    metric="duplicate_title",
                    page=u,
                    severity="medium",
                    evidence=f'Title "{title}" is identical across {len(urls)} crawled pages (e.g. {urls[:2]!r}).',
                    suggested_fix="Provide each page with a distinctive, descriptive title to prevent internal keyword cannibalization.",
                ))

    for desc, urls in desc_pages.items():
        if desc and len(urls) > 1:
            for u in urls:
                findings.append(finding(
                    metric="duplicate_meta_description",
                    page=u,
                    severity="low",
                    evidence=f'Meta description "{desc[:50]}..." is duplicated across {len(urls)} pages.',
                    suggested_fix="Write unique meta descriptions tailored to the specific content and purpose of each page.",
                ))

    # 16. Optional AI Fix Enhancement Layer
    if ai and ai.is_available:
        ai_enhanced_count = 0
        max_ai_enhancements = 8  # Keep audit snappy and respect rate limits
        for f_item in findings:
            if ai_enhanced_count >= max_ai_enhancements:
                break
            # Enhance high-value fixes like missing title, meta descriptions, schema, or headings
            if f_item["metric"] in ("meta_description_missing", "structured_data_missing", "title_missing", "heading_hierarchy_skip"):
                # Find matching page text
                p_match = next((p for p in pages if p.final_url == f_item["page"]), None)
                p_text = visible_text(BeautifulSoup(p_match.html, "html.parser")) if p_match and p_match.html else ""
                p_title = ""
                if p_match and p_match.html:
                    s_tmp = BeautifulSoup(p_match.html, "html.parser")
                    p_title = s_tmp.title.get_text(strip=True) if s_tmp.title else ""

                enhanced = ai.enhance_suggested_fix(
                    metric=f_item["metric"],
                    evidence=f_item["evidence"],
                    page_title=p_title,
                    page_snippet=p_text[:400],
                    default_fix=f_item["suggested_fix"],
                )
                if enhanced and enhanced != f_item["suggested_fix"]:
                    f_item["suggested_fix"] = enhanced
                    ai_enhanced_count += 1

    return findings


def run(
    url: str,
    output: str,
    max_pages: int = 150,
    timeout: float = 12.0,
    concurrency: int = 5,
    ai_provider: ProviderType = "auto",
    ai_model: str | None = None,
) -> list[dict]:
    ai = AIProvider(provider=ai_provider, model=ai_model)
    crawler = SiteCrawler(url, max_pages=max_pages, timeout=timeout, concurrency=concurrency)
    pages = crawler.crawl()
    result = audit(pages, crawler=crawler, ai=ai)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    return result
