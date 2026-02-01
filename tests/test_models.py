"""Tests for the data models."""

from datetime import datetime
from pathlib import Path

from docscrape.core.models import (
    DiscoveredUrl,
    DocumentPage,
    ScrapeConfig,
    ScrapeManifest,
    ScrapeStatus,
)


class TestScrapeConfig:
    """Tests for ScrapeConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ScrapeConfig(
            output_dir=Path("./output"),
            base_url="https://example.com",
        )
        assert config.platform == "generic"
        assert config.max_pages == 0
        assert config.request_delay == 0.5
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.include_patterns == []
        assert config.exclude_patterns == []
        assert config.resume is False
        assert config.verbose is False


class TestDiscoveredUrl:
    """Tests for DiscoveredUrl."""

    def test_hash_and_equality(self):
        """Test hashing and equality based on URL."""
        url1 = DiscoveredUrl(url="https://example.com/a")
        url2 = DiscoveredUrl(url="https://example.com/a")
        url3 = DiscoveredUrl(url="https://example.com/b")

        assert url1 == url2
        assert url1 != url3
        assert hash(url1) == hash(url2)
        assert hash(url1) != hash(url3)

    def test_can_be_used_in_set(self):
        """Test that DiscoveredUrl can be used in sets."""
        urls = {
            DiscoveredUrl(url="https://example.com/a"),
            DiscoveredUrl(url="https://example.com/a"),  # duplicate
            DiscoveredUrl(url="https://example.com/b"),
        }
        assert len(urls) == 2


class TestDocumentPage:
    """Tests for DocumentPage."""

    def test_auto_word_count(self):
        """Test automatic word count calculation."""
        page = DocumentPage(
            url="https://example.com",
            title="Test",
            content_markdown="This is a test with seven words.",
        )
        assert page.word_count == 7  # "This", "is", "a", "test", "with", "seven", "words."

    def test_explicit_word_count(self):
        """Test that explicit word count overrides auto-calculation."""
        page = DocumentPage(
            url="https://example.com",
            title="Test",
            content_markdown="Short content",
            word_count=100,
        )
        assert page.word_count == 100


class TestScrapeManifest:
    """Tests for ScrapeManifest."""

    def test_to_dict(self):
        """Test converting manifest to dictionary."""
        manifest = ScrapeManifest(
            platform="test",
            base_url="https://example.com",
            output_dir="./output",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            successful=10,
            failed=2,
        )
        data = manifest.to_dict()

        assert data["platform"] == "test"
        assert data["base_url"] == "https://example.com"
        assert data["stats"]["successful"] == 10
        assert data["stats"]["failed"] == 2

    def test_from_dict(self):
        """Test creating manifest from dictionary."""
        data = {
            "platform": "test",
            "base_url": "https://example.com",
            "output_dir": "./output",
            "started_at": "2024-01-01T12:00:00",
            "completed_at": None,
            "stats": {
                "total_urls": 12,
                "successful": 10,
                "failed": 2,
                "skipped": 0,
            },
            "pages": [],
            "failed_urls": [],
        }
        manifest = ScrapeManifest.from_dict(data)

        assert manifest.platform == "test"
        assert manifest.successful == 10
        assert manifest.failed == 2

    def test_roundtrip(self):
        """Test that to_dict and from_dict are inverses."""
        original = ScrapeManifest(
            platform="test",
            base_url="https://example.com",
            output_dir="./output",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            completed_at=datetime(2024, 1, 1, 13, 0, 0),
            total_urls=15,
            successful=10,
            failed=5,
        )
        data = original.to_dict()
        restored = ScrapeManifest.from_dict(data)

        assert restored.platform == original.platform
        assert restored.successful == original.successful
        assert restored.failed == original.failed
        assert restored.total_urls == original.total_urls


class TestScrapeStatus:
    """Tests for ScrapeStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert ScrapeStatus.PENDING.value == "pending"
        assert ScrapeStatus.IN_PROGRESS.value == "in_progress"
        assert ScrapeStatus.SUCCESS.value == "success"
        assert ScrapeStatus.FAILED.value == "failed"
        assert ScrapeStatus.SKIPPED.value == "skipped"
