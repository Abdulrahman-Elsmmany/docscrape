"""Tests for the adapter modules."""

from pathlib import Path

import pytest

from docscrape.adapters.factory import PlatformAdapterFactory
from docscrape.adapters.generic import GenericAdapter
from docscrape.adapters.livekit import LiveKitAdapter
from docscrape.adapters.pipecat import PipecatAdapter
from docscrape.adapters.retellai import RetellAIAdapter


class TestPlatformAdapterFactory:
    """Tests for the PlatformAdapterFactory."""

    def test_get_adapter_by_platform_livekit(self):
        """Test getting LiveKit adapter by platform name."""
        adapter = PlatformAdapterFactory.get_adapter(platform="livekit")
        assert isinstance(adapter, LiveKitAdapter)
        assert adapter.name == "livekit"

    def test_get_adapter_by_platform_pipecat(self):
        """Test getting Pipecat adapter by platform name."""
        adapter = PlatformAdapterFactory.get_adapter(platform="pipecat")
        assert isinstance(adapter, PipecatAdapter)
        assert adapter.name == "pipecat"

    def test_get_adapter_by_platform_retellai(self):
        """Test getting RetellAI adapter by platform name."""
        adapter = PlatformAdapterFactory.get_adapter(platform="retellai")
        assert isinstance(adapter, RetellAIAdapter)
        assert adapter.name == "retellai"

    def test_get_adapter_by_url_autodetect(self):
        """Test auto-detecting adapter from URL."""
        adapter = PlatformAdapterFactory.get_adapter(url="https://docs.livekit.io/agents")
        assert isinstance(adapter, LiveKitAdapter)

    def test_get_adapter_by_url_generic_fallback(self):
        """Test falling back to generic adapter for unknown URLs."""
        adapter = PlatformAdapterFactory.get_adapter(url="https://example.com/docs")
        assert isinstance(adapter, GenericAdapter)
        assert adapter.base_url == "https://example.com/docs"

    def test_get_adapter_raises_without_args(self):
        """Test that get_adapter raises without platform or url."""
        with pytest.raises(ValueError, match="Either platform or url must be provided"):
            PlatformAdapterFactory.get_adapter()

    def test_list_platforms(self):
        """Test listing available platforms."""
        platforms = PlatformAdapterFactory.list_platforms()
        assert "livekit" in platforms
        assert "pipecat" in platforms
        assert "retellai" in platforms


class TestGenericAdapter:
    """Tests for the GenericAdapter."""

    def test_extract_content(self, sample_html):
        """Test extracting content from HTML."""
        adapter = GenericAdapter(base_url="https://example.com")
        page = adapter.extract_content(sample_html, "https://example.com/page")

        assert page.title == "Test Page"
        assert "Test Page Title" in page.content_markdown
        assert "test content" in page.content_markdown
        assert "Navigation" not in page.content_markdown  # nav should be removed
        assert "Footer" not in page.content_markdown  # footer should be removed

    def test_url_to_filepath(self):
        """Test URL to filepath conversion."""
        adapter = GenericAdapter(base_url="https://example.com")
        output_dir = Path("/output")

        # Regular path
        result = adapter.url_to_filepath("https://example.com/docs/page", output_dir)
        assert result == Path("/output/docs/page.md")

        # Root path
        result = adapter.url_to_filepath("https://example.com/", output_dir)
        assert result == Path("/output/index.md")

        # Path with .html extension
        result = adapter.url_to_filepath("https://example.com/docs/page.html", output_dir)
        assert result == Path("/output/docs/page.md")


class TestLiveKitAdapter:
    """Tests for the LiveKitAdapter."""

    def test_should_skip_api_reference(self):
        """Test that API reference pages are skipped."""
        adapter = LiveKitAdapter()
        assert adapter.should_skip("https://docs.livekit.io/api-reference/foo")
        assert not adapter.should_skip("https://docs.livekit.io/agents/overview")

    def test_should_skip_changelog(self):
        """Test that changelog pages are skipped."""
        adapter = LiveKitAdapter()
        assert adapter.should_skip("https://docs.livekit.io/changelog")

    def test_url_priority_agents(self):
        """Test URL priority for agents pages."""
        adapter = LiveKitAdapter()
        assert adapter.get_url_priority("https://docs.livekit.io/agents/overview") == 100

    def test_url_priority_guides(self):
        """Test URL priority for guides pages."""
        adapter = LiveKitAdapter()
        assert adapter.get_url_priority("https://docs.livekit.io/guides/foo") == 80


class TestPipecatAdapter:
    """Tests for the PipecatAdapter."""

    def test_should_skip_api(self):
        """Test that API pages are skipped (except overview)."""
        adapter = PipecatAdapter()
        assert adapter.should_skip("https://docs.pipecat.ai/api/reference")
        assert not adapter.should_skip("https://docs.pipecat.ai/api/overview")

    def test_url_priority_quickstart(self):
        """Test URL priority for quickstart pages."""
        adapter = PipecatAdapter()
        assert adapter.get_url_priority("https://docs.pipecat.ai/quickstart") == 100


class TestRetellAIAdapter:
    """Tests for the RetellAIAdapter."""

    def test_should_skip_api_reference(self):
        """Test that API reference pages are skipped."""
        adapter = RetellAIAdapter()
        assert adapter.should_skip("https://docs.retellai.com/api-reference/foo")

    def test_url_priority_conversation_flow(self):
        """Test URL priority for conversation flow pages."""
        adapter = RetellAIAdapter()
        priority = adapter.get_url_priority(
            "https://docs.retellai.com/conversation-flow/guide"
        )
        assert priority == 100
