"""Discovery strategy using recursive link crawling."""

import asyncio
import re
from collections import deque
from typing import AsyncIterator, Optional
from urllib.parse import ParseResult, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from docscrape.core.interfaces import DiscoveryStrategy
from docscrape.core.models import DiscoveredUrl, ScrapeConfig


class RecursiveCrawlDiscovery(DiscoveryStrategy):
    """Discover URLs by recursively crawling links."""

    def __init__(
        self,
        max_depth: int = 5,
        content_selector: Optional[str] = None,
    ) -> None:
        """Initialize the discovery strategy.

        Args:
            max_depth: Maximum depth to crawl.
            content_selector: CSS selector for the content area to find links.
        """
        self._max_depth = max_depth
        self._content_selector = content_selector

    @property
    def name(self) -> str:
        return "recursive"

    async def discover(
        self, config: ScrapeConfig
    ) -> AsyncIterator[DiscoveredUrl]:
        """Discover URLs by crawling links recursively.

        Args:
            config: Scrape configuration.

        Yields:
            DiscoveredUrl objects for each found URL.
        """
        base_url = config.base_url.rstrip("/")
        parsed_base = urlparse(base_url)

        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(base_url, 0)])

        async with httpx.AsyncClient() as client:
            while queue:
                url, depth = queue.popleft()

                # Normalize URL
                url = self._normalize_url(url)

                if url in visited:
                    continue

                if depth > self._max_depth:
                    continue

                visited.add(url)

                # Apply filters
                if not self._should_process(url, base_url, config):
                    continue

                if config.verbose:
                    print(f"Discovering (depth={depth}): {url}")

                try:
                    response = await client.get(
                        url,
                        timeout=config.timeout,
                        follow_redirects=True,
                    )

                    if response.status_code != 200:
                        continue

                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type:
                        continue

                    html = response.text
                    title = self._extract_title(html)

                    # Yield this URL
                    yield DiscoveredUrl(
                        url=url,
                        title=title,
                        priority=max(0, 100 - depth * 10),  # Higher priority for shallower pages
                    )

                    # Find links to add to queue
                    if depth < self._max_depth:
                        links = self._extract_links(html, url, parsed_base)
                        for link in links:
                            if link not in visited:
                                queue.append((link, depth + 1))

                    # Rate limiting
                    await asyncio.sleep(config.request_delay)

                except httpx.HTTPError as e:
                    if config.verbose:
                        print(f"Error fetching {url}: {e}")

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL for deduplication."""
        # Remove fragment
        if "#" in url:
            url = url.split("#")[0]
        # Remove trailing slash for consistency
        url = url.rstrip("/")
        return url

    def _should_process(self, url: str, base_url: str, config: ScrapeConfig) -> bool:
        """Check if a URL should be processed."""
        # Must be under base URL
        if not url.startswith(base_url):
            return False

        # Apply include filters
        if config.include_patterns:
            if not any(re.search(p, url) for p in config.include_patterns):
                return False

        # Apply exclude filters
        if config.exclude_patterns:
            if any(re.search(p, url) for p in config.exclude_patterns):
                return False

        # Skip common non-doc paths
        skip_patterns = [
            r"/api/",
            r"/assets/",
            r"/static/",
            r"/_next/",
            r"/images/",
            r"\.(png|jpg|gif|svg|css|js|woff|ttf)$",
        ]
        for pattern in skip_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False

        return True

    def _extract_title(self, html: str) -> Optional[str]:
        """Extract the page title from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Try various title sources
        if soup.title and soup.title.string:
            return soup.title.string.strip()

        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return None

    def _extract_links(
        self, html: str, current_url: str, parsed_base: ParseResult
    ) -> list[str]:
        """Extract links from HTML content."""
        soup = BeautifulSoup(html, "html.parser")

        # If a content selector is specified, only look for links there
        if self._content_selector:
            content = soup.select_one(self._content_selector)
            if content:
                soup = content

        links: list[str] = []

        for a in soup.find_all("a", href=True):
            href = a["href"]

            # Skip javascript, mailto, tel links
            if href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue

            # Resolve relative URLs
            if href.startswith("/"):
                full_url = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            elif not href.startswith("http"):
                full_url = urljoin(current_url, href)
            else:
                full_url = href

            # Only include URLs on the same domain
            parsed_link = urlparse(full_url)
            if parsed_link.netloc == parsed_base.netloc:
                links.append(self._normalize_url(full_url))

        return links
