"""Discovery strategy using sitemap.xml files."""

import re
import xml.etree.ElementTree as ET
from typing import AsyncIterator, Optional
from urllib.parse import urljoin

import httpx

from docscrape.core.interfaces import DiscoveryStrategy
from docscrape.core.models import DiscoveredUrl, ScrapeConfig


class SitemapDiscovery(DiscoveryStrategy):
    """Discover URLs from sitemap.xml files."""

    # XML namespace for sitemaps
    SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def __init__(self, sitemap_paths: Optional[list[str]] = None) -> None:
        """Initialize the discovery strategy.

        Args:
            sitemap_paths: Paths to sitemap files (relative to base URL).
                          Defaults to ["/sitemap.xml", "/sitemap_index.xml"].
        """
        self._sitemap_paths = sitemap_paths or ["/sitemap.xml", "/sitemap_index.xml"]

    @property
    def name(self) -> str:
        return "sitemap"

    async def discover(
        self, config: ScrapeConfig
    ) -> AsyncIterator[DiscoveredUrl]:
        """Discover URLs from sitemap.xml.

        Args:
            config: Scrape configuration.

        Yields:
            DiscoveredUrl objects for each found URL.
        """
        base_url = config.base_url.rstrip("/")

        async with httpx.AsyncClient() as client:
            # Try each sitemap path
            for path in self._sitemap_paths:
                sitemap_url = urljoin(base_url + "/", path.lstrip("/"))

                if config.verbose:
                    print(f"Trying sitemap at {sitemap_url}...")

                try:
                    response = await client.get(
                        sitemap_url,
                        timeout=config.timeout,
                        follow_redirects=True,
                    )
                    if response.status_code == 200:
                        urls = await self._parse_sitemap(
                            client, response.text, base_url, config
                        )
                        for url in urls:
                            yield url
                        return  # Found a working sitemap
                except httpx.HTTPError as e:
                    if config.verbose:
                        print(f"Failed to fetch {sitemap_url}: {e}")

    async def _parse_sitemap(
        self,
        client: httpx.AsyncClient,
        content: str,
        base_url: str,
        config: ScrapeConfig,
    ) -> list[DiscoveredUrl]:
        """Parse a sitemap XML file.

        Args:
            client: HTTP client for fetching nested sitemaps.
            content: XML content.
            base_url: Base URL.
            config: Scrape configuration.

        Returns:
            List of discovered URLs.
        """
        urls: list[DiscoveredUrl] = []

        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            if config.verbose:
                print(f"Failed to parse sitemap XML: {e}")
            return urls

        # Check if this is a sitemap index
        if root.tag.endswith("sitemapindex"):
            # This is a sitemap index, fetch all child sitemaps
            for sitemap in root.findall("sm:sitemap", self.SITEMAP_NS):
                loc = sitemap.find("sm:loc", self.SITEMAP_NS)
                if loc is not None and loc.text:
                    try:
                        response = await client.get(
                            loc.text,
                            timeout=config.timeout,
                            follow_redirects=True,
                        )
                        if response.status_code == 200:
                            child_urls = await self._parse_sitemap(
                                client, response.text, base_url, config
                            )
                            urls.extend(child_urls)
                    except httpx.HTTPError:
                        pass
        else:
            # This is a regular sitemap
            for url_elem in root.findall("sm:url", self.SITEMAP_NS):
                loc = url_elem.find("sm:loc", self.SITEMAP_NS)
                if loc is not None and loc.text:
                    url = loc.text.strip()

                    # Filter by base URL
                    if not url.startswith(base_url):
                        continue

                    # Apply include/exclude filters
                    if config.include_patterns:
                        if not any(re.search(p, url) for p in config.include_patterns):
                            continue

                    if config.exclude_patterns:
                        if any(re.search(p, url) for p in config.exclude_patterns):
                            continue

                    # Extract priority if available
                    priority_elem = url_elem.find("sm:priority", self.SITEMAP_NS)
                    priority = 0
                    if priority_elem is not None and priority_elem.text:
                        try:
                            priority = int(float(priority_elem.text) * 100)
                        except ValueError:
                            pass

                    urls.append(
                        DiscoveredUrl(
                            url=url,
                            priority=priority,
                            metadata={
                                "lastmod": self._get_text(url_elem, "lastmod"),
                                "changefreq": self._get_text(url_elem, "changefreq"),
                            },
                        )
                    )

        if config.verbose:
            print(f"Found {len(urls)} URLs in sitemap")

        return urls

    def _get_text(self, elem: ET.Element, tag: str) -> Optional[str]:
        """Get text from a child element."""
        child = elem.find(f"sm:{tag}", self.SITEMAP_NS)
        return child.text if child is not None else None
