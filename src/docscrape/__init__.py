"""
docscrape - Scrape any documentation site to Markdown in seconds.

A CLI tool for scraping reference documentation from various platforms
for use as development context.

Usage:
    docscrape https://docs.example.com
    docscrape https://docs.pipecat.ai -o ./my-docs
"""

__version__ = "0.2.0"
__author__ = "Abdulrahman Elsmmany"

from docscrape.core.interfaces import (
    DiscoveryStrategy,
    PlatformAdapter,
    StorageBackend,
)
from docscrape.core.models import (
    CrawlResult,
    DiscoveredUrl,
    DocumentPage,
    ScrapeConfig,
    ScrapeManifest,
    ScrapeStatus,
)

__all__ = [
    "__version__",
    # Models
    "CrawlResult",
    "DiscoveredUrl",
    "DocumentPage",
    "ScrapeConfig",
    "ScrapeManifest",
    "ScrapeStatus",
    # Interfaces
    "DiscoveryStrategy",
    "PlatformAdapter",
    "StorageBackend",
]
