from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict

from bs4 import BeautifulSoup

from .crawler import Page, SiteCrawler


# Comprehensive address abbreviation mapping
ADDRESS_ABBR = {
    r"\bstreet\b": "st",
    r"\broad\b": "rd",
    r"\bavenue\b": "ave",
    r"\bboulevard\b": "blvd",
    r"\bdrive\b": "dr",
    r"\blane\b": "ln",
    r"\bcourt\b": "ct",
    r"\bsuite\b": "ste",
    r"\bapartment\b": "apt",
    r"\bbuilding\b": "bldg",
    r"\bfloor\b": "fl",
    r"\bhighway\b": "hwy",
    r"\bparkway\b": "pkwy",
    r"\bcircle\b": "cir",
    r"\bplace\b": "pl",
    r"\bnorth\b": "n",
    r"\bsouth\b": "s",
    r"\beast\b": "e",
    r"\bwest\b": "w",
}

CORP_SUFFIXES = (
    r"\b(inc|incorporated|llc|l\.l\.c\.|ltd|limited|corp|corporation|co|company|gmbh|sa|plc)\b"
)


def norm_name(value: str) -> str:
    if not value:
        return ""
    s = unicodedata.normalize("NFKC", str(value)).casefold()
    s = re.sub(CORP_SUFFIXES, " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_address(value: str) -> str:
    if not value:
        return ""
    s = unicodedata.normalize("NFKC", str(value)).casefold()
    for pat, repl in ADDRESS_ABBR.items():
        s = re.sub(pat, repl, s)
    # Remove punctuation, unit hashtags, commas
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_phone(value: str) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D", "", unicodedata.normalize("NFKC", str(value)))
    # If standard 11-digit North American number starting with 1, normalize to 10 digits
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    # Keep last 10 digits for common country-code formatting differences if length >= 10
    return digits[-10:] if len(digits) >= 10 else digits


def add_candidate(store: dict[str, list], field: str, value: str | None, page: str, source: str) -> None:
    if not value:
        return
    clean_val = " ".join(str(value).split()).strip()
    if not clean_val or len(clean_val) < 2:
        return

    normalizers = {
        "name": norm_name,
        "address": norm_address,
        "phone": norm_phone,
    }
    norm_fn = normalizers.get(field)
    if not norm_fn:
        return
    norm = norm_fn(clean_val)
    if not norm:
        return

    store[field].append({
        "value": clean_val,
        "normalized": norm,
        "page": page,
        "source": source,
    })


def extract_page_nap(page: Page) -> dict[str, list]:
    soup = BeautifulSoup(page.html, "html.parser")
    out: dict[str, list] = defaultdict(list)

    # 1. JSON-LD Structured Data
    for script in soup.find_all("script", type=re.compile(r"application/ld\+json", re.I)):
        raw = script.string or script.get_text()
        try:
            data = json.loads(raw)
        except Exception:
            continue

        def walk(obj):
            if isinstance(obj, dict):
                typ = str(obj.get("@type", ""))
                org_types = (
                    "LocalBusiness", "Organization", "Corporation", "Store", "Restaurant",
                    "MedicalBusiness", "ProfessionalService", "LegalService", "AutoDealer",
                    "FinancialService", "LodgingBusiness", "PostalAddress"
                )
                if any(t in typ for t in org_types):
                    add_candidate(out, "name", obj.get("name") or obj.get("legalName"), page.final_url, "jsonld")
                    add_candidate(out, "phone", obj.get("telephone") or obj.get("phone"), page.final_url, "jsonld")
                    addr = obj.get("address")
                    if isinstance(addr, dict):
                        parts = [
                            addr.get("streetAddress"),
                            addr.get("addressLocality"),
                            addr.get("addressRegion"),
                            addr.get("postalCode"),
                            addr.get("addressCountry"),
                        ]
                        addr_str = ", ".join(str(x) for x in parts if x)
                        add_candidate(out, "address", addr_str, page.final_url, "jsonld")
                    elif isinstance(addr, str):
                        add_candidate(out, "address", addr, page.final_url, "jsonld")
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)

        walk(data)

    # 2. Semantic Microdata (itemprop)
    for el in soup.find_all(attrs={"itemprop": True}):
        prop = str(el.get("itemprop", "")).lower()
        txt = el.get_text(" ", strip=True) or el.get("content", "")
        if "name" in prop.split():
            add_candidate(out, "name", txt, page.final_url, "microdata")
        if "telephone" in prop or "phone" in prop:
            add_candidate(out, "phone", txt, page.final_url, "microdata")
        if "streetaddress" in prop or "postaladdress" in prop or "address" in prop.split():
            add_candidate(out, "address", txt, page.final_url, "microdata")

    # 3. Dedicated HTML5 <address> Elements
    for el in soup.find_all("address"):
        addr_txt = el.get_text(" ", strip=True)
        if addr_txt and len(addr_txt) > 8:
            add_candidate(out, "address", addr_txt, page.final_url, "html_address")

    # 4. Telephony and Contact Links
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if href.lower().startswith("tel:"):
            phone_num = href[4:].split("?")[0].strip()
            add_candidate(out, "phone", phone_num, page.final_url, "tel_link")

    # 5. Open Graph / Meta Branding
    og_site = soup.find("meta", attrs={"property": re.compile(r"^og:site_name$", re.I)})
    if og_site and og_site.get("content"):
        add_candidate(out, "name", og_site.get("content"), page.final_url, "og_site_name")

    # 6. Header / Navbar Brand Links and Logos
    for h in soup.find_all(["header", "nav"]):
        for a in h.find_all("a", href=True):
            href = a.get("href", "").strip().lower()
            is_home_link = href in ("/", "index.html", "./", "") or href.endswith(("/index.html", "/index.php"))
            has_brand_class = any(
                c in " ".join(a.get("class", [])).lower()
                for c in ("logo", "brand", "navbar-brand", "site-title")
            )
            if is_home_link or has_brand_class:
                first_text = a.find(string=True, recursive=False)
                txt = (first_text or a.get_text(" ", strip=True) or "").strip()
                if txt and 2 <= len(txt) <= 60:
                    if txt.lower() not in {"home", "menu", "skip to content", "close", "nav"}:
                        add_candidate(out, "name", txt, page.final_url, "header_brand")

    # Logo image alt text
    for img in soup.find_all("img"):
        src = (img.get("src") or "").lower()
        cls = " ".join(img.get("class", [])).lower()
        img_id = (img.get("id") or "").lower()
        if any(k in src or k in cls or k in img_id for k in ("logo", "brand")):
            alt = (img.get("alt") or "").strip()
            if alt and 2 <= len(alt) <= 60:
                cleaned = re.sub(r"(?i)\s+(logo|icon|image)$", "", alt).strip()
                if cleaned and cleaned.lower() not in {"logo", "icon", "image"}:
                    add_candidate(out, "name", cleaned, page.final_url, "logo_alt")

    # 7. Contact Sections and Footer Parsing
    contact_containers = soup.find_all(["footer", "section", "div"], class_=re.compile(r"(footer|contact|location|address)", re.I))
    for container in contact_containers:
        text = container.get_text(" ", strip=True)
        # Copyright notice for business name
        copy_match = re.search(
            r"(?:©|&copy;|copyright)\s*(?:\d{4}(?:\s*-\s*\d{4})?)?\s*([A-Za-z0-9\s.,&-]+?)(?:\.|\s+all rights|\s*$)",
            text,
            re.IGNORECASE
        )
        if copy_match:
            c_name = copy_match.group(1).strip()
            if 3 <= len(c_name) <= 60 and c_name.lower() not in {"all rights reserved"}:
                add_candidate(out, "name", c_name, page.final_url, "footer_copyright")

        # Phone regex
        for m in re.findall(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text):
            add_candidate(out, "phone", m, page.final_url, "footer_text")
        # Address regex heuristic: number + street name + city/state/zip
        addr_matches = re.findall(
            r"\b\d{1,5}\s+[A-Za-z0-9\s.,#-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Suite|Ste|Way)\b[A-Za-z0-9\s,.-]+(?:\d{5}(?:-\d{4})?)?",
            text,
            re.IGNORECASE
        )
        for m in addr_matches:
            if len(m.strip()) > 12:
                add_candidate(out, "address", m.strip(), page.final_url, "footer_address")

    return out


def build_field_report(field: str, candidates: list[dict], total_pages_crawled: int) -> dict:
    if not candidates:
        return {
            "field": field,
            "pages_compared": [],
            "values": [],
            "normalized_values": [],
            "confidence": 0.0,
            "confidence_explanation": f"No business {field} indicators were detected on any crawled page.",
            "verdict": "not_found",
        }

    # Group by normalized value
    groups: dict[str, list[dict]] = defaultdict(list)
    for c in candidates:
        groups[c["normalized"]].append(c)

    # Sort groups by number of occurrences (descending)
    sorted_groups = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)

    pages_compared = sorted({c["page"] for c in candidates})
    values_output = []
    normalized_values = []

    for norm_val, group in sorted_groups:
        normalized_values.append(norm_val)
        pages_with_val = sorted({c["page"] for c in group})
        sources_with_val = sorted({c["source"] for c in group})
        values_output.append({
            "value": group[0]["value"],
            "normalized": norm_val,
            "pages": pages_with_val,
            "occurrences": len(group),
            "sources": sources_with_val,
        })

    is_consistent = (len(groups) == 1)
    num_pages = len(pages_compared)
    num_sources = len({c["source"] for c in candidates})
    has_structured = any(c["source"] in ("jsonld", "microdata", "tel_link") for c in candidates)

    if is_consistent:
        verdict = "consistent"
        # High confidence if verified across multiple pages or structured markup
        base_conf = 0.80
        if num_pages >= 2:
            base_conf += 0.10
        if has_structured:
            base_conf += 0.06
        if num_sources >= 2:
            base_conf += 0.03
        confidence = round(min(0.99, base_conf), 2)
        explanation = (
            f"Consistent {field} verified across {num_pages} page(s) and {num_sources} source(s) "
            f"({', '.join(values_output[0]['sources'])}) with 0 discrepancies."
        )
    else:
        verdict = "mismatch"
        # Confidence reflects certainty that a true mismatch exists
        diff_count = len(groups)
        conf = 0.70 + 0.08 * min(num_pages, 3)
        confidence = round(min(0.98, conf), 2)
        explanation = (
            f"Found {diff_count} conflicting normalized {field} values across {num_pages} pages "
            f"(e.g. '{values_output[0]['normalized']}' vs '{values_output[1]['normalized']}'). "
            "The mismatch stems from distinct content rather than formatting differences."
        )

    return {
        "field": field,
        "pages_compared": pages_compared,
        "values": values_output,
        "normalized_values": normalized_values,
        "confidence": confidence,
        "confidence_explanation": explanation,
        "verdict": verdict,
    }


def audit_nap(pages: list[Page]) -> list[dict]:
    collected: dict[str, list] = defaultdict(list)
    for p in pages:
        if not p.html:
            continue
        page_data = extract_page_nap(p)
        for fld, items in page_data.items():
            collected[fld].extend(items)

    total_pages = len(pages)
    report = []
    for fld in ("name", "address", "phone"):
        field_rep = build_field_report(fld, collected.get(fld, []), total_pages)
        report.append(field_rep)

    return report


def run(url: str, output: str, max_pages: int = 150, timeout: float = 12.0, concurrency: int = 5) -> list[dict]:
    crawler = SiteCrawler(url, max_pages=max_pages, timeout=timeout, concurrency=concurrency)
    pages = crawler.crawl()
    result = audit_nap(pages)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    return result
