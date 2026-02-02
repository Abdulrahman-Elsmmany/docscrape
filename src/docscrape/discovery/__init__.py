"""URL discovery strategies for documentation sites."""

from docscrape.discovery.llms_txt import LlmsTxtDiscovery
from docscrape.discovery.recursive import RecursiveCrawlDiscovery
from docscrape.discovery.sitemap import SitemapDiscovery

__all__ = [
    "LlmsTxtDiscovery",
    "SitemapDiscovery",
    "RecursiveCrawlDiscovery",
]
