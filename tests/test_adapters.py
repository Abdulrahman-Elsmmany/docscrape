"""Tests for the adapter modules."""

from pathlib import Path

from docscrape.adapters.generic import GenericAdapter


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

    def test_content_quality_validation(self, mintlify_html):
        """Test that content quality validation prefers larger content elements.

        When a small .prose element exists in the header and the real content
        is in #content, the adapter should select #content.
        """
        adapter = GenericAdapter(base_url="https://example.com")
        page = adapter.extract_content(mintlify_html, "https://example.com/page")

        # Should contain the full content from #content, not just the small .prose header
        assert "Configuration Parameters" in page.content_markdown
        assert "event_handler" in page.content_markdown
        assert "on_participant_joined" in page.content_markdown

    def test_content_quality_fallback_to_short_element(self):
        """Test that a short element is used as fallback when no large content exists."""
        html = """
        <html><body>
            <div class="prose">Short content here.</div>
        </body></html>
        """
        adapter = GenericAdapter(base_url="https://example.com")
        page = adapter.extract_content(html, "https://example.com/page")

        assert "Short content" in page.content_markdown

    def test_copy_button_removed(self):
        """Test that .copy-button elements are removed during extraction."""
        html = """
        <html><body>
            <main>
                <h1>Code Example</h1>
                <pre><code>print("hello")</code></pre>
                <button class="copy-button">Copy</button>
                <p>Some explanation text here that is meaningful.</p>
            </main>
        </body></html>
        """
        adapter = GenericAdapter(base_url="https://example.com")
        page = adapter.extract_content(html, "https://example.com/page")

        assert "Copy" not in page.content_markdown
        assert "print" in page.content_markdown
