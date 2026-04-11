"""Tests for the CLI module."""

from pathlib import Path

from docscrape.cli import _derive_output_from_url


class TestDeriveOutputFromUrl:
    """Tests for URL to output directory derivation."""

    def test_docs_subdomain(self):
        """Test docs.* subdomain extraction with no path."""
        result = _derive_output_from_url("https://docs.pipecat.ai")
        assert result == Path("./pipecat/")

    def test_docs_subdomain_with_path(self):
        """Test docs.* subdomain with a path segment is nested under the slug."""
        result = _derive_output_from_url("https://docs.livekit.io/agents")
        assert result == Path("./livekit/agents/")

    def test_www_subdomain(self):
        """Test www.* subdomain removal, with path segment preserved."""
        result = _derive_output_from_url("https://www.example.com/docs")
        assert result == Path("./example/docs/")

    def test_plain_domain(self):
        """Test plain domain extraction with path segment preserved."""
        result = _derive_output_from_url("https://example.com/docs")
        assert result == Path("./example/docs/")

    def test_developer_subdomain(self):
        """Test developer.* subdomain removal."""
        result = _derive_output_from_url("https://developer.example.com")
        assert result == Path("./example/")

    def test_hyphenated_domain(self):
        """Test hyphenated domain names."""
        result = _derive_output_from_url("https://docs.my-project.io")
        assert result == Path("./my-project/")

    def test_sibling_projects_same_domain_no_overwrite(self):
        """Sibling projects under the same domain must land in separate dirs.

        Regression: before the path-aware fix, docs.astral.sh/{uv,ruff,ty}
        all resolved to ./astral/ and clobbered each other's _manifest.json.
        """
        assert _derive_output_from_url("https://docs.astral.sh/uv") == Path("./astral/uv/")
        assert _derive_output_from_url("https://docs.astral.sh/ruff") == Path("./astral/ruff/")
        assert _derive_output_from_url("https://docs.astral.sh/ty") == Path("./astral/ty/")

    def test_deep_path_readthedocs_style(self):
        """Multi-segment paths like readthedocs version paths are preserved."""
        result = _derive_output_from_url("https://xgboost.readthedocs.io/en/release_3.2.0/")
        assert result == Path("./xgboost/en/release_3.2.0/")
