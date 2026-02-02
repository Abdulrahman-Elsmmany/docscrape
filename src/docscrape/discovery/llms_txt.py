"""Discovery strategy using llms.txt files.

Many documentation sites provide an llms.txt file that lists all pages
in a format optimized for LLM consumption. This strategy parses that file.
"""

import re
from collections.abc import AsyncIterator
from urllib.parse import urljoin

import httpx

from docscrape.core.interfaces import DiscoveryStrategy
from docscrape.core.models import DiscoveredUrl, ScrapeConfig


class LlmsTxtDiscovery(DiscoveryStrategy):
    """Discover URLs from an llms.txt file."""

    def __init__(self, llms_txt_path: str = "/llms.txt") -> None:
        """Initialize the discovery strategy.

        Args:
            llms_txt_path: Path to the llms.txt file (relative to base URL).
        """
        self._llms_txt_path = llms_txt_path

    @property
    def name(self) -> str:
        return "llms_txt"

    async def discover(self, config: ScrapeConfig) -> AsyncIterator[DiscoveredUrl]:
        """Discover URLs from llms.txt file.

        Args:
            config: Scrape configuration.

        Yields:
            DiscoveredUrl objects for each found URL.
        """
        llms_txt_url = urljoin(config.base_url.rstrip("/") + "/", self._llms_txt_path.lstrip("/"))

        if config.verbose:
            print(f"Fetching llms.txt from {llms_txt_url}...")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    llms_txt_url,
                    timeout=config.timeout,
                    follow_redirects=True,
                )
                response.raise_for_status()
                content = response.text
            except httpx.HTTPError as e:
                if config.verbose:
                    print(f"Failed to fetch llms.txt: {e}")
                return

        urls = self._extract_urls(content, config.base_url)

        if config.verbose:
            print(f"Found {len(urls)} URLs in llms.txt")

        for url_info in urls:
            # Apply include/exclude filters
            if config.include_patterns and not any(
                re.search(p, url_info.url) for p in config.include_patterns
            ):
                continue

            if config.exclude_patterns and any(
                re.search(p, url_info.url) for p in config.exclude_patterns
            ):
                continue

            yield url_info

    def _extract_urls(self, content: str, base_url: str) -> list[DiscoveredUrl]:
        """Extract URLs from llms.txt content.

        Args:
            content: Raw llms.txt content.
            base_url: Base URL to resolve relative links.

        Returns:
            List of discovered URLs with metadata.
        """
        urls: dict[str, DiscoveredUrl] = {}
        base_url = base_url.rstrip("/")

        # Pattern for absolute URLs
        abs_url_pattern = re.compile(rf'{re.escape(base_url)}[^\s\)\]>"\']+(?:\.md|\.html|/)?')

        # Pattern for markdown links: [title](url)
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^\)]+)\)")

        # Pattern for bare URLs ending in .md
        md_pattern = re.compile(r'(https?://[^\s\)\]>"\']+\.md)')

        # Find all markdown links first (they have titles)
        for match in link_pattern.finditer(content):
            title = match.group(1).strip()
            url = match.group(2).strip()

            # Resolve relative URLs
            if url.startswith("/"):
                url = base_url + url
            elif not url.startswith("http"):
                url = urljoin(base_url + "/", url)

            # Clean up URL
            url = self._clean_url(url)

            if self._is_doc_url(url, base_url):
                if url not in urls:
                    urls[url] = DiscoveredUrl(url=url, title=title)
                elif urls[url].title is None:
                    urls[url].title = title

        # Find bare absolute URLs
        for match in abs_url_pattern.finditer(content):
            url = self._clean_url(match.group(0))
            if self._is_doc_url(url, base_url) and url not in urls:
                urls[url] = DiscoveredUrl(url=url)

        # Find .md URLs
        for match in md_pattern.finditer(content):
            url = self._clean_url(match.group(1))
            if self._is_doc_url(url, base_url) and url not in urls:
                urls[url] = DiscoveredUrl(url=url)

        return list(urls.values())

    def _clean_url(self, url: str) -> str:
        """Clean up a URL."""
        # Remove trailing punctuation
        url = url.rstrip(".,;:)'\"")
        # Remove fragment identifiers for deduplication
        if "#" in url:
            url = url.split("#")[0]
        return url

    def _is_doc_url(self, url: str, base_url: str) -> bool:
        """Check if a URL is a documentation URL."""
        if not url.startswith(base_url):
            return False

        # Skip non-doc paths
        skip_patterns = [
            "/api/",
            "/cdn/",
            "/assets/",
            "/static/",
            "/_next/",
            "/images/",
        ]
        return all(pattern not in url for pattern in skip_patterns)
