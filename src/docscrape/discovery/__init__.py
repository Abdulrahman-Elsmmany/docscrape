"""URL discovery strategies for documentation sites."""

from docscrape.discovery.llms_txt import LlmsTxtDiscovery
from docscrape.discovery.sitemap import SitemapDiscovery
from docscrape.discovery.recursive import RecursiveCrawlDiscovery

__all__ = [
    "LlmsTxtDiscovery",
    "SitemapDiscovery",
    "RecursiveCrawlDiscovery",
]
