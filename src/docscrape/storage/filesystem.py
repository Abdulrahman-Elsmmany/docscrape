"""Filesystem storage backend for scraped documentation."""

import json
from pathlib import Path
from typing import Any, Optional

from docscrape.core.interfaces import StorageBackend
from docscrape.core.models import DocumentPage, ScrapeManifest


class FilesystemStorage(StorageBackend):
    """Store scraped documentation on the local filesystem."""

    MANIFEST_FILENAME = "_manifest.json"
    INDEX_FILENAME = "_index.md"

    async def save_page(self, page: DocumentPage, filepath: Path) -> None:
        """Save a page to the filesystem.

        Args:
            page: Page to save.
            filepath: Target filepath.
        """
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Build markdown content with frontmatter
        content = self._build_page_content(page)

        # Write file
        filepath.write_text(content, encoding="utf-8")

    async def load_manifest(self, output_dir: Path) -> Optional[ScrapeManifest]:
        """Load an existing manifest.

        Args:
            output_dir: Directory containing the manifest.

        Returns:
            Manifest if it exists, None otherwise.
        """
        manifest_path = output_dir / self.MANIFEST_FILENAME

        if not manifest_path.exists():
            return None

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return ScrapeManifest.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load manifest: {e}")
            return None

    async def save_manifest(self, manifest: ScrapeManifest, output_dir: Path) -> None:
        """Save a manifest.

        Args:
            manifest: Manifest to save.
            output_dir: Target directory.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = output_dir / self.MANIFEST_FILENAME
        manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2),
            encoding="utf-8",
        )

        # Also generate a human-readable index
        await self._generate_index(manifest, output_dir)

    async def page_exists(self, filepath: Path) -> bool:
        """Check if a page already exists.

        Args:
            filepath: Path to check.

        Returns:
            True if the page exists.
        """
        return filepath.exists()

    def get_completed_urls(self, manifest: ScrapeManifest) -> set[str]:
        """Get URLs that have already been successfully scraped.

        Args:
            manifest: Manifest to check.

        Returns:
            Set of completed URLs.
        """
        return {page["url"] for page in manifest.pages}

    def _build_page_content(self, page: DocumentPage) -> str:
        """Build the full page content with frontmatter.

        Args:
            page: Page to format.

        Returns:
            Formatted markdown content.
        """
        lines = [
            "---",
            f'title: "{page.title.replace(chr(34), chr(39))}"',
            f"url: {page.url}",
            f"scraped_at: {page.scraped_at.isoformat()}",
            f"word_count: {page.word_count}",
            "---",
            "",
            page.content_markdown,
        ]

        return "\n".join(lines)

    async def _generate_index(
        self, manifest: ScrapeManifest, output_dir: Path
    ) -> None:
        """Generate a human-readable index file.

        Args:
            manifest: Manifest to index.
            output_dir: Output directory.
        """
        index_path = output_dir / self.INDEX_FILENAME

        lines = [
            f"# {manifest.platform.title()} Documentation Index",
            "",
            f"**Source:** {manifest.base_url}",
            f"**Scraped:** {manifest.started_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Statistics",
            "",
            f"- Total URLs: {manifest.total_urls}",
            f"- Successful: {manifest.successful}",
            f"- Failed: {manifest.failed}",
            "",
            "## Pages",
            "",
        ]

        # Group pages by directory
        pages_by_dir: dict[str, list[dict[str, Any]]] = {}
        for page in sorted(manifest.pages, key=lambda p: p["filepath"]):
            filepath = Path(page["filepath"])
            try:
                dir_path = str(filepath.parent.relative_to(output_dir))
            except ValueError:
                dir_path = str(filepath.parent)
            if dir_path == ".":
                dir_path = "root"

            if dir_path not in pages_by_dir:
                pages_by_dir[dir_path] = []
            pages_by_dir[dir_path].append(page)

        # Generate index entries
        for dir_name, pages in sorted(pages_by_dir.items()):
            lines.append(f"### {dir_name}")
            lines.append("")

            for page in pages:
                filepath = Path(page["filepath"])
                try:
                    rel_path = filepath.relative_to(output_dir)
                except ValueError:
                    rel_path = filepath
                title = page.get("title", "Untitled")
                word_count = page.get("word_count", 0)
                lines.append(f"- [{title}]({rel_path}) ({word_count} words)")

            lines.append("")

        # Add failed URLs if any
        if manifest.failed_urls:
            lines.append("## Failed URLs")
            lines.append("")
            for failed in manifest.failed_urls:
                error = failed.get("error", "Unknown error")
                lines.append(f"- {failed['url']}: {error}")
            lines.append("")

        index_path.write_text("\n".join(lines), encoding="utf-8")
