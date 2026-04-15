"""Discovery strategy backed by a headless browser (crawl4ai / Playwright).

Complements :class:`RecursiveCrawlDiscovery` for sites whose navigation
links are injected by JavaScript. The strategy performs a shallow BFS
using rendered fetches — anything deeper is handled by the
curl_cffi-based recursive strategy which runs in parallel.
"""

import re
from collections import deque
from collections.abc import AsyncIterator
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from docscrape.core.browser_fetch import fetch_rendered
from docscrape.core.interfaces import DiscoveryStrategy
from docscrape.core.models import DiscoveredUrl, ScrapeConfig


class BrowserDiscovery(DiscoveryStrategy):
    """Shallow BFS using a headless browser to discover JS-rendered links."""

    def __init__(self, max_depth: int = 2) -> None:
        self._max_depth = max_depth

    @property
    def name(self) -> str:
        return "browser"

    async def discover(self, config: ScrapeConfig) -> AsyncIterator[DiscoveredUrl]:
        base_url = config.base_url.rstrip("/")
        parsed_base = urlparse(base_url)

        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(base_url, 0)])

        while queue:
            url, depth = queue.popleft()
            url = _normalize(url)

            if url in visited or depth > self._max_depth:
                continue
            visited.add(url)

            if not _should_process(url, base_url, config):
                continue

            response = await fetch_rendered(url, timeout=config.timeout * 2)
            if not response.success or not response.html:
                continue

            title = _extract_title(response.html)
            yield DiscoveredUrl(
                url=url,
                title=title,
                priority=max(0, 100 - depth * 10),
            )

            if depth < self._max_depth:
                for link in _extract_links(response.html, url, parsed_base.netloc):
                    link = _normalize(link)
                    if link not in visited:
                        queue.append((link, depth + 1))


def _normalize(url: str) -> str:
    if "#" in url:
        url = url.split("#")[0]
    return url.rstrip("/")


def _should_process(url: str, base_url: str, config: ScrapeConfig) -> bool:
    if not url.startswith(base_url):
        return False
    if config.include_patterns and not any(
        re.search(p, url) for p in config.include_patterns
    ):
        return False
    if config.exclude_patterns and any(
        re.search(p, url) for p in config.exclude_patterns
    ):
        return False
    skip = [
        r"/assets/",
        r"/static/",
        r"/_next/",
        r"/images/",
        r"\.(png|jpg|gif|svg|css|js|woff|ttf)$",
    ]
    return all(not re.search(p, url, re.IGNORECASE) for p in skip)


def _extract_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return None


def _extract_links(html: str, current_url: str, base_netloc: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[str] = []
    for a in soup.find_all("a", href=True):
        href = str(a["href"])
        if href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        if href.startswith("/"):
            parsed = urlparse(current_url)
            href = f"{parsed.scheme}://{parsed.netloc}{href}"
        elif not href.startswith("http"):
            href = urljoin(current_url, href)
        if urlparse(href).netloc == base_netloc:
            out.append(href)
    return out
