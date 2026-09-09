from __future__ import annotations

import re
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

USER_AGENT = "SEOAuditAgent/2.0 (+https://github.com/seo-audit-agent; free-evaluation-bot)"
HTML_TYPES = {"text/html", "application/xhtml+xml"}


@dataclass
class Page:
    url: str
    status: int
    content_type: str
    html: str
    final_url: str
    error: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    response_time: float = 0.0
    referrers: list[str] = field(default_factory=list)


def normalize_url(url: str, base: str | None = None) -> str:
    if not url:
        return ""
    if base:
        url = urljoin(base, url)
    url, _ = urldefrag(url)
    p = urlparse(url)
    scheme = p.scheme.lower() or "https"
    if scheme not in {"http", "https"}:
        return ""
    host = (p.hostname or "").lower()
    if not host:
        return ""
    port = p.port
    if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        port = None
    netloc = host if port is None else f"{host}:{port}"
    path = p.path or "/"
    # Clean redundant trailing dots or slashes where reasonable, keep root as /
    path = re.sub(r"/+", "/", path)
    return urlunparse((scheme, netloc, path, "", p.query, ""))


def same_site(url: str, root: str) -> bool:
    if not url or not root:
        return False
    a, b = urlparse(url), urlparse(root)
    if a.scheme not in {"http", "https"}:
        return False
    ah = (a.hostname or "").lower().removeprefix("www.")
    bh = (b.hostname or "").lower().removeprefix("www.")
    return ah == bh


def is_crawlable_link(url: str) -> bool:
    if not url:
        return False
    p = urlparse(url)
    if p.scheme not in {"http", "https"}:
        return False
    path = p.path.lower()
    blocked_ext = (
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp", ".tiff",
        ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z", ".exe", ".dmg",
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv",
        ".mp4", ".mp3", ".webm", ".avi", ".mov", ".wav", ".ogg",
        ".css", ".js", ".mjs", ".xml", ".json", ".woff", ".woff2", ".ttf", ".eot",
    )
    return not path.endswith(blocked_ext)


def url_priority_score(url: str) -> int:
    """Prioritize pages likely to contain contact, legal, or high-value NAP data."""
    u = url.lower()
    score = 10
    if any(k in u for k in ("contact", "about", "location", "store", "reach-us", "get-in-touch")):
        score += 50
    elif any(k in u for k in ("privacy", "terms", "legal", "faq", "help", "support")):
        score += 30
    elif urlparse(u).path in {"", "/"}:
        score += 40
    return score


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
    })
    return s


def load_robots(session: requests.Session, root: str) -> RobotFileParser:
    p = urlparse(root)
    rp = RobotFileParser()
    rp.set_url(f"{p.scheme}://{p.netloc}/robots.txt")
    try:
        r = session.get(f"{p.scheme}://{p.netloc}/robots.txt", timeout=8.0)
        if r.ok and r.text.strip():
            rp.parse(r.text.splitlines())
        else:
            rp.allow_all = True
    except Exception:
        rp.allow_all = True
    return rp


def extract_sitemaps(session: requests.Session, root: str, timeout: float = 10.0) -> list[str]:
    candidates = []
    p = urlparse(root)
    rp_url = f"{p.scheme}://{p.netloc}/robots.txt"
    try:
        r = session.get(rp_url, timeout=timeout)
        if r.ok:
            candidates.extend(re.findall(r"(?im)^\s*Sitemap:\s*(\S+)", r.text))
    except requests.RequestException:
        pass
    candidates.append(f"{p.scheme}://{p.netloc}/sitemap.xml")
    candidates.append(f"{p.scheme}://{p.netloc}/sitemap_index.xml")
    return list(dict.fromkeys(normalize_url(x) for x in candidates if x))


def sitemap_urls(session: requests.Session, root: str, timeout: float = 10.0, max_urls: int = 500) -> list[str]:
    found = []
    seen_maps = set()
    queue = deque(extract_sitemaps(session, root, timeout))
    while queue and len(found) < max_urls:
        sm = queue.popleft()
        if not sm or sm in seen_maps or not same_site(sm, root):
            continue
        seen_maps.add(sm)
        try:
            r = session.get(sm, timeout=timeout)
        except requests.RequestException:
            continue
        if not r.ok:
            continue
        try:
            soup = BeautifulSoup(r.text, "xml")
        except Exception:
            soup = BeautifulSoup(r.text, "html.parser")

        for loc in soup.find_all("loc"):
            u = normalize_url(loc.get_text(strip=True))
            if not u or not same_site(u, root):
                continue
            # Check if this loc points to another sitemap
            if soup.find("sitemap") and loc.parent and loc.parent.name == "sitemap":
                queue.append(u)
            else:
                if is_crawlable_link(u):
                    found.append(u)
    return list(dict.fromkeys(found))[:max_urls]


class SiteCrawler:
    def __init__(
        self,
        root_url: str,
        max_pages: int = 150,
        timeout: float = 12.0,
        delay: float = 0.05,
        concurrency: int = 5,
    ):
        self.root_url = normalize_url(root_url)
        if not self.root_url:
            raise ValueError(f"Invalid root URL: {root_url}")
        self.max_pages = max_pages
        self.timeout = timeout
        self.delay = delay
        self.concurrency = max(1, min(concurrency, 10))
        self.session = make_session()
        self.robots = load_robots(self.session, self.root_url)
        self._lock = threading.Lock()
        self.referrers: dict[str, list[str]] = {}

    def allowed(self, url: str) -> bool:
        try:
            if getattr(self.robots, "allow_all", False):
                return True
            return self.robots.can_fetch(USER_AGENT, url)
        except Exception:
            return True

    def fetch(self, url: str) -> Page | None:
        if not self.allowed(url):
            return None
        t0 = time.perf_counter()
        try:
            r = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            elapsed = time.perf_counter() - t0
        except requests.RequestException as e:
            elapsed = time.perf_counter() - t0
            refs = self.referrers.get(url, [])
            return Page(
                url=url,
                status=0,
                content_type="",
                html="",
                final_url=url,
                error=str(e),
                headers={},
                response_time=round(elapsed, 3),
                referrers=refs,
            )

        ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
        headers_dict = {k.lower(): v for k, v in r.headers.items()}
        refs = self.referrers.get(url, [])

        if ctype not in HTML_TYPES:
            return Page(
                url=url,
                status=r.status_code,
                content_type=ctype,
                html="",
                final_url=r.url,
                headers=headers_dict,
                response_time=round(elapsed, 3),
                referrers=refs,
            )

        return Page(
            url=url,
            status=r.status_code,
            content_type=ctype,
            html=r.text,
            final_url=r.url,
            headers=headers_dict,
            response_time=round(elapsed, 3),
            referrers=refs,
        )

    def crawl(self) -> list[Page]:
        # Collect initial seed URLs
        sitemap_seeds = sitemap_urls(
            self.session, self.root_url, self.timeout, max_urls=max(self.max_pages * 2, 200)
        )
        seeds = [self.root_url] + [u for u in sitemap_seeds if same_site(u, self.root_url)]
        seeds = list(dict.fromkeys(seeds))

        # Track frontier and visited URLs
        visited: set[str] = set()
        queued: set[str] = set(seeds)
        pages: list[Page] = []
        frontier = deque(sorted(seeds, key=url_priority_score, reverse=True))

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            active_futures = {}

            def submit_next():
                while frontier and len(pages) + len(active_futures) < self.max_pages:
                    url = frontier.popleft()
                    if url not in visited:
                        visited.add(url)
                        fut = executor.submit(self.fetch, url)
                        active_futures[fut] = url

            submit_next()

            while active_futures and len(pages) < self.max_pages:
                # Wait for any future to complete
                done = []
                for fut in as_completed(active_futures):
                    done.append(fut)
                    break  # Process one by one for responsiveness

                for fut in done:
                    orig_url = active_futures.pop(fut)
                    try:
                        page = fut.result()
                    except Exception as e:
                        page = Page(
                            url=orig_url,
                            status=0,
                            content_type="",
                            html="",
                            final_url=orig_url,
                            error=str(e),
                            referrers=self.referrers.get(orig_url, []),
                        )

                    if page is not None:
                        pages.append(page)

                        # Extract internal links from fetched HTML
                        if page.html and page.status < 400:
                            try:
                                soup = BeautifulSoup(page.html, "html.parser")
                                new_links = []
                                for a in soup.find_all("a", href=True):
                                    nxt = normalize_url(a["href"], page.final_url)
                                    if nxt and same_site(nxt, self.root_url) and is_crawlable_link(nxt):
                                        # Record referrer for internal link graph
                                        with self._lock:
                                            if page.final_url not in self.referrers.setdefault(nxt, []):
                                                self.referrers[nxt].append(page.final_url)
                                        if nxt not in visited and nxt not in queued:
                                            queued.add(nxt)
                                            new_links.append(nxt)
                                # Sort newly discovered links by priority
                                new_links.sort(key=url_priority_score, reverse=True)
                                frontier.extend(new_links)
                            except Exception:
                                pass

                    if self.delay > 0:
                        time.sleep(self.delay)

                    submit_next()

        # Update referrers on all page objects
        for p in pages:
            if not p.referrers and p.url in self.referrers:
                p.referrers = self.referrers[p.url]

        return pages
