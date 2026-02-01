"""Abstract interfaces for docscrape."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator, Optional

from docscrape.core.models import (
    DiscoveredUrl,
    DocumentPage,
    ScrapeConfig,
    ScrapeManifest,
)


class DiscoveryStrategy(ABC):
    """Abstract base class for URL discovery strategies."""

    @abstractmethod
    async def discover(
        self, config: ScrapeConfig
    ) -> AsyncIterator[DiscoveredUrl]:
        """Discover URLs to scrape.

        Args:
            config: Scrape configuration.

        Yields:
            DiscoveredUrl objects for each found URL.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this discovery strategy."""
        ...


class PlatformAdapter(ABC):
    """Abstract base class for platform-specific adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the platform name."""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base URL for this platform's documentation."""
        ...

    @abstractmethod
    def get_discovery_strategy(self) -> DiscoveryStrategy:
        """Return the preferred discovery strategy for this platform."""
        ...

    @abstractmethod
    def extract_content(self, html: str, url: str) -> DocumentPage:
        """Extract content from HTML.

        Args:
            html: Raw HTML content.
            url: Source URL.

        Returns:
            Extracted DocumentPage with markdown content.
        """
        ...

    @abstractmethod
    def url_to_filepath(self, url: str, output_dir: Path) -> Path:
        """Convert a URL to a local filepath.

        Args:
            url: Source URL.
            output_dir: Base output directory.

        Returns:
            Local filepath for storing the content.
        """
        ...

    def should_skip(self, url: str) -> bool:
        """Check if a URL should be skipped.

        Args:
            url: URL to check.

        Returns:
            True if the URL should be skipped.
        """
        return False

    def get_url_priority(self, url: str) -> int:
        """Get the priority for a URL (higher = more important).

        Args:
            url: URL to check.

        Returns:
            Priority value (default 0).
        """
        return 0


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def save_page(self, page: DocumentPage, filepath: Path) -> None:
        """Save a page to storage.

        Args:
            page: Page to save.
            filepath: Target filepath.
        """
        ...

    @abstractmethod
    async def load_manifest(self, output_dir: Path) -> Optional[ScrapeManifest]:
        """Load an existing manifest.

        Args:
            output_dir: Directory containing the manifest.

        Returns:
            Manifest if it exists, None otherwise.
        """
        ...

    @abstractmethod
    async def save_manifest(self, manifest: ScrapeManifest, output_dir: Path) -> None:
        """Save a manifest.

        Args:
            manifest: Manifest to save.
            output_dir: Target directory.
        """
        ...

    @abstractmethod
    async def page_exists(self, filepath: Path) -> bool:
        """Check if a page already exists.

        Args:
            filepath: Path to check.

        Returns:
            True if the page exists.
        """
        ...

    @abstractmethod
    def get_completed_urls(self, manifest: ScrapeManifest) -> set[str]:
        """Get URLs that have already been successfully scraped.

        Args:
            manifest: Manifest to check.

        Returns:
            Set of completed URLs.
        """
        ...
