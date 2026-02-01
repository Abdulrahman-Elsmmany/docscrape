"""Tests for the CLI module."""

from pathlib import Path

from docscrape.cli import _derive_output_from_url


class TestDeriveOutputFromUrl:
    """Tests for URL to output directory derivation."""

    def test_docs_subdomain(self):
        """Test docs.* subdomain extraction."""
        result = _derive_output_from_url("https://docs.pipecat.ai")
        assert result == Path("./pipecat/")

    def test_docs_subdomain_with_path(self):
        """Test docs.* subdomain with path."""
        result = _derive_output_from_url("https://docs.livekit.io/agents")
        assert result == Path("./livekit/")

    def test_www_subdomain(self):
        """Test www.* subdomain removal."""
        result = _derive_output_from_url("https://www.example.com/docs")
        assert result == Path("./example/")

    def test_plain_domain(self):
        """Test plain domain extraction."""
        result = _derive_output_from_url("https://example.com/docs")
        assert result == Path("./example/")

    def test_developer_subdomain(self):
        """Test developer.* subdomain removal."""
        result = _derive_output_from_url("https://developer.example.com")
        assert result == Path("./example/")

    def test_hyphenated_domain(self):
        """Test hyphenated domain names."""
        result = _derive_output_from_url("https://docs.my-project.io")
        assert result == Path("./my-project/")
