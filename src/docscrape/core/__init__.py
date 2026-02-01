"""Core models and interfaces for docscrape."""

from docscrape.core.models import (
    CrawlResult,
    DiscoveredUrl,
    DocumentPage,
    ScrapeConfig,
    ScrapeManifest,
    ScrapeStatus,
)
from docscrape.core.interfaces import (
    DiscoveryStrategy,
    PlatformAdapter,
    StorageBackend,
)

__all__ = [
    "CrawlResult",
    "DiscoveredUrl",
    "DocumentPage",
    "ScrapeConfig",
    "ScrapeManifest",
    "ScrapeStatus",
    "DiscoveryStrategy",
    "PlatformAdapter",
    "StorageBackend",
]
