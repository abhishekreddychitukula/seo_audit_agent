from __future__ import annotations

import json
import math
import re
from collections import Counter
from typing import TypedDict

from bs4 import BeautifulSoup

from .crawler import SiteCrawler


# Comprehensive stopword list for English query filtering
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're",
    "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with",
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've",
    "your", "yours", "yourself", "yourselves", "tell", "show", "give", "find",
    "please",
}


def simple_stem(word: str) -> str:
    """Lightweight, deterministic suffix stemmer without third-party dependencies."""
    w = word.lower()
    if len(w) <= 3:
        return w
    if w.endswith("sses"):
        w = w[:-2]
    elif w.endswith("ies"):
        w = w[:-3] + "y"
    elif w.endswith("ss"):
        pass
    elif w.endswith("s") and not w.endswith("us") and not w.endswith("is"):
        w = w[:-1]

    for suffix in ("ing", "ed", "ly", "ment", "tion", "able", "ible"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            w = w[:-len(suffix)]
            break

    # Strip trailing silent 'e' so e.g. 'service' and 'services' map to the same stem
    if w.endswith("e") and len(w) >= 4:
        w = w[:-1]

    return w


def extract_query_tokens(query: str) -> list[str]:
    raw = re.findall(r"\b[A-Za-z0-9][A-Za-z0-9'-]*\b", query.lower())
    return [w for w in raw if w not in STOPWORDS and len(w) > 1]


def extract_passages_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg", "nav", "footer"]):
        tag.decompose()

    passages = []
    seen = set()

    # 1. Composite FAQ / Heading + Content blocks
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "dt"])
    for h in headings:
        h_text = h.get_text(" ", strip=True)
        # Find next sibling with content
        nxt = h.find_next_sibling(["p", "ul", "ol", "dd", "div"])
        if nxt and h_text:
            nxt_text = nxt.get_text(" ", strip=True)
            if nxt_text and len(nxt_text) > 15:
                composite = f"{h_text}: {nxt_text}"
                if composite not in seen and len(composite) < 800:
                    seen.add(composite)
                    passages.append(composite)

    # 2. Discrete semantic text containers
    semantic_tags = ["p", "li", "dd", "blockquote", "td", "th"]
    for el in soup.find_all(semantic_tags):
        raw_text = el.get_text(" ", strip=True)
        clean_text = re.sub(r"\s+", " ", raw_text).strip()
        if 25 <= len(clean_text) <= 1000:
            if clean_text not in seen:
                seen.add(clean_text)
                passages.append(clean_text)

    # 3. Leaf block containers (e.g. alert divs, callout banners, cards without nested blocks)
    for el in soup.find_all(["div", "article", "section", "aside"]):
        # Only take leaf containers that don't contain other nested paragraphs or sections
        if not el.find_all(["div", "p", "ul", "ol", "table", "article", "section"]):
            raw_text = el.get_text(" ", strip=True)
            clean_text = re.sub(r"\s+", " ", raw_text).strip()
            if 25 <= len(clean_text) <= 1000:
                if clean_text not in seen:
                    seen.add(clean_text)
                    passages.append(clean_text)

    return passages


class PassageDoc:
    def __init__(self, url: str, text: str):
        self.url = url
        self.text = text
        self.raw_tokens = [w.lower() for w in re.findall(r"\b[A-Za-z0-9][A-Za-z0-9'-]*\b", text)]
        self.stemmed_tokens = [simple_stem(t) for t in self.raw_tokens if t not in STOPWORDS]
        self.term_counts = Counter(self.stemmed_tokens)
        self.length = len(self.stemmed_tokens)


class AnswerResult(TypedDict):
    query: str
    url: str | None
    excerpt: str | None


def compute_bm25_and_coverage(
    query_tokens: list[str],
    doc: PassageDoc,
    doc_freqs: dict[str, int],
    total_docs: int,
    avg_doc_len: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> tuple[float, float]:
    stemmed_query = [simple_stem(q) for q in query_tokens]
    query_set = set(stemmed_query)

    score = 0.0
    matched_query_terms = 0

    for q_stem in query_set:
        f = doc.term_counts.get(q_stem, 0)
        if f > 0:
            matched_query_terms += 1
            n_q = doc_freqs.get(q_stem, 1)
            idf = math.log(1.0 + (total_docs - n_q + 0.5) / (n_q + 0.5))
            term_score = idf * ((f * (k1 + 1)) / (f + k1 * (1 - b + b * (doc.length / max(1.0, avg_doc_len)))))
            score += term_score

    coverage = matched_query_terms / max(1, len(query_set))

    # Exact multi-word phrase bonus
    q_norm = " ".join(query_tokens)
    doc_norm = " ".join(doc.raw_tokens)
    if len(query_tokens) >= 2 and q_norm in doc_norm:
        score += 3.0

    return score, coverage


def answer(url: str, query: str, max_pages: int = 150, timeout: float = 12.0, concurrency: int = 5) -> AnswerResult:
    clean_query = query.strip()
    q_tokens = extract_query_tokens(clean_query)

    if not q_tokens:
        return {"query": clean_query, "url": None, "excerpt": None}

    crawler = SiteCrawler(url, max_pages=max_pages, timeout=timeout, concurrency=concurrency)
    pages = crawler.crawl()

    documents: list[PassageDoc] = []
    doc_freqs: Counter[str] = Counter()

    for p in pages:
        if not p.html or p.status >= 400:
            continue
        raw_passages = extract_passages_from_html(p.html)
        for raw_text in raw_passages:
            doc = PassageDoc(url=p.final_url, text=raw_text)
            if doc.length > 0:
                documents.append(doc)
                for unique_term in set(doc.stemmed_tokens):
                    doc_freqs[unique_term] += 1

    if not documents:
        return {"query": clean_query, "url": None, "excerpt": None}

    total_docs = len(documents)
    avg_doc_len = sum(d.length for d in documents) / total_docs

    best_doc: PassageDoc | None = None
    best_score = -1.0
    best_coverage = 0.0

    for doc in documents:
        score, coverage = compute_bm25_and_coverage(q_tokens, doc, doc_freqs, total_docs, avg_doc_len)
        if score > best_score:
            best_score = score
            best_coverage = coverage
            best_doc = doc

    # Grounding verification: require sufficient keyword coverage & BM25 score
    min_coverage_threshold = 0.50 if len(q_tokens) >= 2 else 1.0
    min_bm25_threshold = 1.8

    if (
        best_doc is not None
        and best_coverage >= min_coverage_threshold
        and best_score >= min_bm25_threshold
    ):
        return {
            "query": clean_query,
            "url": best_doc.url,
            "excerpt": best_doc.text,
        }

    # Strict refusal to guess: return null when unsupported by the site markup
    return {
        "query": clean_query,
        "url": None,
        "excerpt": None,
    }


def run(url: str, query: str, output: str, max_pages: int = 150, timeout: float = 12.0, concurrency: int = 5) -> AnswerResult:
    result = answer(url, query, max_pages=max_pages, timeout=timeout, concurrency=concurrency)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    return result
