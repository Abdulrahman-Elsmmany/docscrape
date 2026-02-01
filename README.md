# docscrape

> Scrape any documentation site to Markdown in seconds.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**docscrape** converts any documentation website into clean Markdown files perfect for:

- **AI/LLM Context** - Feed docs to Claude, GPT, or local models
- **Offline Reading** - Access docs without internet
- **RAG Pipelines** - Build searchable knowledge bases
- **Development Context** - Keep reference docs in your project

## Quick Start

```bash
# Install (with uv)
uv tool install docscrape

# Or with pip
pip install docscrape

# Scrape any docs - just paste the URL
docscrape https://docs.pipecat.ai
```

That's it! Output is auto-saved to `./pipecat/` (derived from URL).

## Installation

### Using pip

```bash
# From PyPI
pip install docscrape

# From GitHub (latest)
pip install git+https://github.com/Abdulrahman-Elsmmany/docscrape
```

### Using uv (recommended)

```bash
# Install globally
uv tool install docscrape

# Or from GitHub
uv tool install git+https://github.com/Abdulrahman-Elsmmany/docscrape

# Run without installing
uvx docscrape https://docs.example.com
```

### For Development

```bash
git clone https://github.com/Abdulrahman-Elsmmany/docscrape
cd docscrape

# With uv (recommended)
uv venv
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

## Usage

### Basic Usage

```bash
# Scrape docs - output auto-detected from URL
docscrape https://docs.example.com

# Custom output directory
docscrape https://docs.example.com -o ./my-docs

# Limit pages (useful for testing)
docscrape https://docs.example.com -m 50

# Verbose output
docscrape https://docs.example.com -v
```

### Resume Interrupted Scrapes

```bash
# Start a scrape
docscrape https://docs.example.com -v

# ... connection drops, press Ctrl+C, etc ...

# Resume from where you left off
docscrape https://docs.example.com -r
```

### Filter URLs

```bash
# Only include certain paths
docscrape https://docs.example.com -i "/guides/"

# Exclude certain paths
docscrape https://docs.example.com -e "/api-reference/"

# Combine filters
docscrape https://docs.example.com -i "/guides/" -e "/deprecated/"
```

## Command Reference

```
docscrape [URL] [OPTIONS]

Arguments:
  URL                    Documentation URL to scrape

Options:
  -o, --output PATH      Output directory [default: auto-detected]
  -m, --max-pages INT    Maximum pages to scrape (0 = unlimited)
  -d, --delay FLOAT      Delay between requests in seconds [default: 0.5]
  -r, --resume           Resume from previous scrape
  -v, --verbose          Show detailed progress
  -i, --include PATTERN  URL patterns to include (regex)
  -e, --exclude PATTERN  URL patterns to exclude (regex)
  -V, --version          Show version
  --help                 Show help
```

### List Optimized Platforms

```bash
docscrape platforms
```

```
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Platform ┃ Base URL                   ┃ Discovery ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ livekit  │ https://docs.livekit.io   │ llms_txt  │
│ pipecat  │ https://docs.pipecat.ai   │ sitemap   │
│ retellai │ https://docs.retellai.com │ sitemap   │
└──────────┴────────────────────────────┴───────────┘
Note: Any documentation site works! These platforms have optimized adapters.
```

## Output Structure

```
./pipecat/
├── _index.md           # Human-readable index
├── _manifest.json      # Machine-readable metadata
├── index.md            # Homepage
├── quickstart.md
├── guides/
│   ├── getting-started.md
│   └── advanced.md
└── api/
    └── overview.md
```

### Markdown Files

Each file includes YAML frontmatter:

```markdown
---
title: "Getting Started with Pipecat"
url: https://docs.pipecat.ai/guides/getting-started
scraped_at: 2024-01-15T10:30:00
word_count: 1523
---

# Getting Started with Pipecat

...
```

## Features

| Feature | Description |
|---------|-------------|
| **Universal** | Works with any documentation site |
| **Smart Defaults** | Auto-detects output folder from URL |
| **Resumable** | Continue interrupted scrapes with `-r` |
| **Clean Output** | Markdown with YAML frontmatter |
| **Rate Limited** | Respects servers with configurable delays |
| **Optimized Adapters** | Better extraction for known platforms |

## Discovery Strategies

docscrape uses multiple strategies to find documentation pages:

1. **llms.txt** - Many docs provide an LLM-friendly index
2. **sitemap.xml** - Standard sitemap discovery
3. **Recursive Crawl** - Follow links when no sitemap exists

## Architecture

```
docscrape/
├── cli.py              # Command-line interface
├── core/
│   ├── models.py       # Data models (ScrapeConfig, DocumentPage, etc.)
│   └── interfaces.py   # Abstract base classes
├── adapters/
│   ├── factory.py      # Platform auto-detection
│   ├── generic.py      # Works with any site
│   ├── livekit.py      # LiveKit-specific
│   ├── pipecat.py      # Pipecat-specific
│   └── retellai.py     # RetellAI-specific
├── discovery/
│   ├── sitemap.py      # Sitemap.xml parsing
│   ├── llms_txt.py     # llms.txt parsing
│   └── recursive.py    # Link crawling
├── engine/
│   └── crawler.py      # Async crawl orchestration
└── storage/
    └── filesystem.py   # Local file storage
```

## Adding Custom Adapters

Create optimized adapters for specific documentation sites:

```python
from docscrape.adapters.generic import GenericAdapter
from docscrape.adapters.factory import PlatformAdapterFactory

class MyDocsAdapter(GenericAdapter):
    BASE_URL = "https://docs.mysite.com"

    def __init__(self):
        super().__init__(
            base_url=self.BASE_URL,
            content_selectors=["article", "main"],
        )

    @property
    def name(self) -> str:
        return "mysite"

    def should_skip(self, url: str) -> bool:
        return "/changelog/" in url

# Register the adapter
PlatformAdapterFactory.register_platform(
    "mysite",
    MyDocsAdapter,
    url_patterns=["docs.mysite.com"],
)
```

## Development

```bash
# Clone the repo
git clone https://github.com/Abdulrahman-Elsmmany/docscrape
cd docscrape

# Setup with uv (recommended)
uv venv
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/

# Type checking
mypy src/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

Made with by [Abdulrahman Elsmmany](https://github.com/Abdulrahman-Elsmmany)
