"""Adapter for RetellAI documentation."""

from pathlib import Path
from urllib.parse import urlparse

from docscrape.adapters.generic import GenericAdapter
from docscrape.core.interfaces import DiscoveryStrategy
from docscrape.discovery.sitemap import SitemapDiscovery
from docscrape.discovery.recursive import RecursiveCrawlDiscovery


class RetellAIAdapter(GenericAdapter):
    """Adapter for RetellAI documentation (docs.retellai.com)."""

    BASE_URL = "https://docs.retellai.com"

    def __init__(self) -> None:
        """Initialize the RetellAI adapter."""
        super().__init__(
            base_url=self.BASE_URL,
            content_selectors=[
                "article",
                ".markdown-body",
                "main",
                ".prose",
                ".content",
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
                "script",
                "style",
            ],
        )

    @property
    def name(self) -> str:
        return "retellai"

    def get_discovery_strategy(self) -> DiscoveryStrategy:
        """Try sitemap first."""
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
        # Skip API reference pages (usually auto-generated)
        if "/api-reference/" in url:
            return True

        return False

    def get_url_priority(self, url: str) -> int:
        """Get priority for URL ordering."""
        # Prioritize conversation flow documentation (main interest)
        if "conversation-flow" in url.lower():
            return 100
        if "/quickstart" in url:
            return 95
        if "/getting-started" in url:
            return 90
        if "/concepts" in url:
            return 85
        if "/examples" in url:
            return 80
        if "/guides" in url:
            return 75
        if "/custom-llm" in url:
            return 70

        return 50
