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


@pytest.fixture
def mintlify_html():
    """Mintlify-like HTML with multiple .prose elements of different sizes.

    Simulates the Pipecat docs layout where a small .prose element in the
    header matches first, but the real content lives in #content.
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Daily Transport | Pipecat Docs</title>
        <meta property="og:title" content="Daily Transport">
    </head>
    <body>
        <nav>Navigation sidebar</nav>
        <header>
            <div class="prose">
                <h1>Daily Transport</h1>
            </div>
        </header>
        <div id="content">
            <h1>Daily Transport</h1>
            <p>The Daily transport enables real-time communication using Daily's WebRTC infrastructure.</p>

            <h2>Configuration Parameters</h2>
            <p>The transport accepts the following configuration options for customizing behavior:</p>
            <ul>
                <li><code>room_url</code> - The Daily room URL to connect to</li>
                <li><code>token</code> - Authentication token for the room</li>
                <li><code>bot_name</code> - Display name for the bot participant</li>
                <li><code>duration</code> - Maximum session duration in seconds</li>
            </ul>

            <h2>Event Handlers</h2>
            <p>Register callbacks for transport events:</p>
            <pre><code class="language-python">
@transport.event_handler("on_participant_joined")
async def on_joined(transport, participant):
    print(f"Participant joined: {participant['id']}")

@transport.event_handler("on_participant_left")
async def on_left(transport, participant):
    print(f"Participant left: {participant['id']}")
            </code></pre>

            <h2>Audio Configuration</h2>
            <p>Configure audio input and output settings for the transport pipeline.</p>
            <pre><code class="language-python">
transport = DailyTransport(
    room_url="https://example.daily.co/room",
    token="your-token",
    bot_name="my-bot",
    params=DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_enabled=True,
    )
)
            </code></pre>

            <h2>Pipeline Integration</h2>
            <p>The Daily transport integrates with the Pipecat pipeline system for processing audio and video frames in real-time applications.</p>
        </div>
        <footer>Footer content</footer>
    </body>
    </html>
    """
