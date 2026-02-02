"""Adapter for LiveKit documentation."""

from pathlib import Path
from urllib.parse import urlparse

from docscrape.adapters.generic import GenericAdapter
from docscrape.core.interfaces import DiscoveryStrategy
from docscrape.discovery.llms_txt import LlmsTxtDiscovery


class LiveKitAdapter(GenericAdapter):
    """Adapter for LiveKit documentation (docs.livekit.io)."""

    BASE_URL = "https://docs.livekit.io"

    def __init__(self) -> None:
        """Initialize the LiveKit adapter."""
        super().__init__(
            base_url=self.BASE_URL,
            content_selectors=[
                "article",
                ".prose",
                "main",
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
        return "livekit"

    def get_discovery_strategy(self) -> DiscoveryStrategy:
        """LiveKit provides an llms.txt file."""
        return LlmsTxtDiscovery()

    def url_to_filepath(self, url: str, output_dir: Path) -> Path:
        """Convert URL to filepath.

        LiveKit URLs often have .md extension already in llms.txt.
        """
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path:
            path = "index.md"
        elif not path.endswith(".md"):
            path = path + ".md"

        return output_dir / path

    def should_skip(self, url: str) -> bool:
        """Check if URL should be skipped."""
        # Skip API reference pages (usually auto-generated)
        if "/api-reference/" in url:
            return True

        # Skip changelog
        return "/changelog" in url

    def get_url_priority(self, url: str) -> int:
        """Get priority for URL ordering."""
        # Prioritize main topics
        if "/agents/" in url:
            return 100
        if "/realtime/" in url:
            return 90
        if "/guides/" in url:
            return 80
        if "/quickstarts/" in url:
            return 70

        return 50
