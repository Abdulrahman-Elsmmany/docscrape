"""Adapter for Pipecat documentation."""

from pathlib import Path
from urllib.parse import urlparse

from docscrape.adapters.generic import GenericAdapter
from docscrape.core.interfaces import DiscoveryStrategy
from docscrape.discovery.recursive import RecursiveCrawlDiscovery
from docscrape.discovery.sitemap import SitemapDiscovery


class PipecatAdapter(GenericAdapter):
    """Adapter for Pipecat documentation (docs.pipecat.ai)."""

    BASE_URL = "https://docs.pipecat.ai"

    def __init__(self) -> None:
        """Initialize the Pipecat adapter."""
        super().__init__(
            base_url=self.BASE_URL,
            content_selectors=[
                "article",
                ".markdown-body",
                "main",
                ".prose",
                "#content",
            ],
            skip_selectors=[
                "nav",
                "header",
                "footer",
                ".sidebar",
                ".toc",
                ".table-of-contents",
                ".navigation",
                ".breadcrumb",
                ".edit-page",
                ".feedback",
                ".copy-button",
                ".tabs",
                "script",
                "style",
            ],
        )

    @property
    def name(self) -> str:
        return "pipecat"

    def get_discovery_strategy(self) -> DiscoveryStrategy:
        """Try sitemap first, fall back to recursive crawl."""
        # Pipecat may use sitemap or we crawl recursively
        return SitemapDiscovery()

    def get_fallback_strategy(self) -> DiscoveryStrategy:
        """Return fallback discovery strategy."""
        return RecursiveCrawlDiscovery(
            max_depth=4,
            content_selector="main",
        )

    def url_to_filepath(self, url: str, output_dir: Path) -> Path:
        """Convert URL to filepath."""
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path:
            path = "index"

        # Remove common extensions
        for ext in [".html", ".htm", ".md"]:
            if path.endswith(ext):
                path = path[: -len(ext)]

        path = path + ".md"

        return output_dir / path

    def should_skip(self, url: str) -> bool:
        """Check if URL should be skipped."""
        # Skip API reference pages
        return "/api/" in url and "/api/overview" not in url

    def get_url_priority(self, url: str) -> int:
        """Get priority for URL ordering."""
        # Prioritize getting started and core concepts
        if "/quickstart" in url:
            return 100
        if "/getting-started" in url:
            return 95
        if "/introduction" in url:
            return 90
        if "/concepts" in url:
            return 85
        if "/examples" in url:
            return 80
        if "/guides" in url:
            return 75

        return 50
