"""Discovery strategy that reads robots.txt for Sitemap: directives."""

import re
from collections.abc import AsyncIterator
from urllib.parse import urljoin, urlparse

from docscrape.core.http import RequestException, make_session
from docscrape.core.interfaces import DiscoveryStrategy
from docscrape.core.models import DiscoveredUrl, ScrapeConfig
from docscrape.discovery.sitemap import SitemapDiscovery


class RobotsTxtDiscovery(DiscoveryStrategy):
    """Discover URLs via sitemaps advertised in robots.txt."""

    @property
    def name(self) -> str:
        return "robots"

    async def discover(self, config: ScrapeConfig) -> AsyncIterator[DiscoveredUrl]:
        base_url = config.base_url.rstrip("/")
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        async with make_session(timeout=config.timeout) as client:
            try:
                response = await client.get(robots_url)
                if response.status_code != 200:
                    return
                sitemap_urls = _extract_sitemaps(response.text, robots_url)
            except RequestException:
                return

            if not sitemap_urls:
                return

            sitemap_strategy = SitemapDiscovery()
            for sitemap_url in sitemap_urls:
                try:
                    sm_response = await client.get(sitemap_url)
                    if sm_response.status_code != 200:
                        continue
                    urls = await sitemap_strategy._parse_sitemap(
                        client, sm_response.text, base_url, config
                    )
                    for url in urls:
                        yield url
                except RequestException:
                    continue


_SITEMAP_RE = re.compile(r"(?im)^\s*sitemap\s*:\s*(\S+)\s*$")


def _extract_sitemaps(robots_txt: str, base: str) -> list[str]:
    """Extract absolute sitemap URLs from robots.txt content."""
    results: list[str] = []
    for match in _SITEMAP_RE.finditer(robots_txt):
        url = match.group(1).strip()
        if not url:
            continue
        if not url.startswith(("http://", "https://")):
            url = urljoin(base, url)
        results.append(url)
    return results
