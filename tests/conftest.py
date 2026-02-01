"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page | Docs</title>
        <meta property="og:title" content="Test Page">
    </head>
    <body>
        <nav>Navigation</nav>
        <main>
            <article>
                <h1>Test Page Title</h1>
                <p>This is some test content.</p>
                <pre><code class="language-python">print("hello")</code></pre>
                <a href="/other-page">Link to other page</a>
            </article>
        </main>
        <footer>Footer</footer>
    </body>
    </html>
    """
