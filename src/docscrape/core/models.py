"""Data models for docscrape."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ScrapeStatus(Enum):
    """Status of a scrape operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ScrapeConfig:
    """Configuration for a scrape operation."""

    output_dir: Path
    base_url: str
    platform: str = "generic"
    max_pages: int = 0  # 0 = unlimited
    request_delay: float = 0.5
    timeout: float = 30.0
    max_retries: int = 3
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    resume: bool = False
    verbose: bool = False
    quiet: bool = False  # Suppress progress bar


@dataclass
class DiscoveredUrl:
    """A URL discovered during the discovery phase."""

    url: str
    title: Optional[str] = None
    priority: int = 0  # Higher = more important
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.url)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DiscoveredUrl):
            return False
        return self.url == other.url


@dataclass
class DocumentPage:
    """A scraped documentation page."""

    url: str
    title: str
    content_markdown: str
    content_html: Optional[str] = None
    filepath: Optional[Path] = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    word_count: int = 0
    links: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.word_count == 0 and self.content_markdown:
            self.word_count = len(self.content_markdown.split())


@dataclass
class CrawlResult:
    """Result of crawling a single URL."""

    url: str
    status: ScrapeStatus
    page: Optional[DocumentPage] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class ScrapeManifest:
    """Manifest tracking the state of a scrape operation."""

    platform: str
    base_url: str
    output_dir: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_urls: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    pages: list[dict[str, Any]] = field(default_factory=list)
    failed_urls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "platform": self.platform,
            "base_url": self.base_url,
            "output_dir": self.output_dir,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "stats": {
                "total_urls": self.total_urls,
                "successful": self.successful,
                "failed": self.failed,
                "skipped": self.skipped,
            },
            "pages": self.pages,
            "failed_urls": self.failed_urls,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScrapeManifest":
        """Create from dictionary (loaded from JSON)."""
        return cls(
            platform=data["platform"],
            base_url=data["base_url"],
            output_dir=data["output_dir"],
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            total_urls=data.get("stats", {}).get("total_urls", 0),
            successful=data.get("stats", {}).get("successful", 0),
            failed=data.get("stats", {}).get("failed", 0),
            skipped=data.get("stats", {}).get("skipped", 0),
            pages=data.get("pages", []),
            failed_urls=data.get("failed_urls", []),
        )
