"""Generic adapter for documentation sites."""

import re
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as md

from docscrape.core.interfaces import DiscoveryStrategy, PlatformAdapter
from docscrape.core.models import DocumentPage
from docscrape.discovery.recursive import RecursiveCrawlDiscovery
from docscrape.discovery.sitemap import SitemapDiscovery

MIN_CONTENT_CHARS = 200


class GenericAdapter(PlatformAdapter):
    """Generic adapter that works with most documentation sites."""

    def __init__(
        self,
        base_url: str,
        content_selectors: list[str] | None = None,
        skip_selectors: list[str] | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            base_url: Base URL of the documentation site.
            content_selectors: CSS selectors for content areas (tried in order).
            skip_selectors: CSS selectors for elements to remove before extraction.
        """
        self._base_url = base_url.rstrip("/")
        self._content_selectors = content_selectors or [
            "#content",  # Mintlify and many doc platforms
            ".mdx-content",  # Mintlify MDX content
            "#main-content",  # Common pattern
            "article",  # Standard HTML5
            "main",  # Standard HTML5
            ".markdown-body",  # GitHub-style
            ".content",  # Generic
            ".documentation",  # Generic
            ".docs-content",  # Generic
            ".prose",  # Tailwind - LAST (matches many elements)
        ]
        self._skip_selectors = skip_selectors or [
            "nav",
            "header",
            "footer",
            ".sidebar",
            ".toc",
            ".table-of-contents",
            ".navigation",
            ".breadcrumb",
            ".edit-page",
            ".feedback",
            ".copy-button",
            "script",
            "style",
        ]

    @property
    def name(self) -> str:
        return "generic"

    @property
    def base_url(self) -> str:
        return self._base_url

    def get_discovery_strategy(self) -> DiscoveryStrategy:
        """Return sitemap discovery as the default strategy."""
        return SitemapDiscovery()

    def get_fallback_strategy(self) -> DiscoveryStrategy:
        """Return recursive crawl as fallback when sitemap discovery fails."""
        return RecursiveCrawlDiscovery(max_depth=5, content_selector="main")

    def extract_content(self, html: str, url: str) -> DocumentPage:
        """Extract content from HTML.

        Args:
            html: Raw HTML content.
            url: Source URL.

        Returns:
            Extracted DocumentPage.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for selector in self._skip_selectors:
            for elem in soup.select(selector):
                elem.decompose()

        # Find content area (prefer elements with substantial text)
        content_elem = None
        for selector in self._content_selectors:
            candidate = soup.select_one(selector)
            if candidate:
                if len(candidate.get_text(strip=True)) >= MIN_CONTENT_CHARS:
                    content_elem = candidate
                    break
                elif content_elem is None:
                    content_elem = candidate  # fallback to first match

        if not content_elem:
            content_elem = soup.body or soup

        # Extract links before converting to markdown
        links = self._extract_links(content_elem, url)

        # Convert to markdown
        markdown = md(
            str(content_elem),
            heading_style="atx",
            code_language_callback=self._detect_language,
        )

        # Clean up markdown
        markdown = self._clean_markdown(markdown)

        # Extract title (pass markdown for fallback extraction)
        title = self._extract_title(soup, markdown)

        return DocumentPage(
            url=url,
            title=title or "Untitled",
            content_markdown=markdown,
            content_html=str(content_elem),
            links=links,
        )

    def url_to_filepath(self, url: str, output_dir: Path) -> Path:
        """Convert URL to filepath.

        Strips the base URL's path prefix from the incoming URL so pages
        land cleanly inside output_dir instead of doubling up the prefix.
        (Necessary because `_derive_output_from_url` now bakes the base
        URL path into output_dir itself.)

        Args:
            url: Source URL.
            output_dir: Base output directory.

        Returns:
            Local filepath.
        """
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # Strip the base URL path prefix if the URL sits under it.
        base_path = urlparse(self._base_url).path.strip("/")
        if base_path and (path == base_path or path.startswith(base_path + "/")):
            path = path[len(base_path) :].strip("/")

        if not path:
            path = "index"

        # Remove common extensions
        for ext in [".html", ".htm", ".md"]:
            if path.endswith(ext):
                path = path[: -len(ext)]

        # Add .md extension
        path = path + ".md"

        return output_dir / path

    def _extract_title(self, soup: BeautifulSoup, markdown: str | None = None) -> str | None:
        """Extract page title."""
        # Try meta title
        meta_title = soup.find("meta", property="og:title")
        if meta_title and meta_title.get("content"):
            return str(meta_title["content"])

        # Try title tag
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            # Remove common suffixes
            for suffix in [" | Docs", " - Documentation", " | Documentation"]:
                if title.endswith(suffix):
                    title = title[: -len(suffix)]
            return title

        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        # Try extracting from markdown content (for raw .md files)
        if markdown:
            # Look for # Title at the start
            h1_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
            if h1_match:
                return h1_match.group(1).strip()

        return None

    def _extract_links(self, content: Tag, current_url: str) -> list[str]:
        """Extract internal links from content."""
        links = []
        base_domain = urlparse(current_url).netloc

        for a in content.find_all("a", href=True):
            href = str(a["href"])

            # Skip anchors and non-http links
            if href.startswith(("#", "javascript:", "mailto:")):
                continue

            # Resolve relative URLs
            if href.startswith("/"):
                parsed = urlparse(current_url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            elif not href.startswith("http"):
                from urllib.parse import urljoin

                href = urljoin(current_url, href)

            # Only include internal links
            if urlparse(href).netloc == base_domain:
                links.append(href)

        return links

    def _detect_language(self, elem: Tag) -> str | None:
        """Detect code language from element classes."""
        if not elem:
            return None

        raw_classes = elem.get("class")
        classes: list[str] = raw_classes if isinstance(raw_classes, list) else []
        for cls in classes:
            if cls.startswith("language-"):
                return cls[9:]
            if cls.startswith("lang-"):
                return cls[5:]
            if cls in [
                "python",
                "javascript",
                "typescript",
                "bash",
                "shell",
                "json",
                "yaml",
            ]:
                return cls

        return None

    def _clean_markdown(self, markdown: str) -> str:
        """Clean up converted markdown."""
        # Remove excessive blank lines
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        # Remove leading/trailing whitespace from lines
        lines = [line.rstrip() for line in markdown.split("\n")]
        markdown = "\n".join(lines)

        # Remove leading/trailing blank lines
        markdown = markdown.strip()

        return markdown
