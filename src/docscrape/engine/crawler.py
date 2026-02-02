"""Documentation crawler using httpx and BeautifulSoup.

This module provides a lightweight crawler for documentation sites,
using httpx for async HTTP requests and BeautifulSoup for HTML parsing.
"""

import asyncio
import time
from collections.abc import AsyncIterator
from datetime import datetime

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from docscrape.core.interfaces import PlatformAdapter, StorageBackend
from docscrape.core.models import (
    CrawlResult,
    DiscoveredUrl,
    DocumentPage,
    ScrapeConfig,
    ScrapeManifest,
    ScrapeStatus,
)

console = Console()


class DocumentationCrawler:
    """Crawler for documentation websites."""

    def __init__(
        self,
        adapter: PlatformAdapter,
        storage: StorageBackend,
        config: ScrapeConfig,
    ) -> None:
        """Initialize the crawler.

        Args:
            adapter: Platform adapter for content extraction.
            storage: Storage backend for saving content.
            config: Scrape configuration.
        """
        self._adapter = adapter
        self._storage = storage
        self._config = config
        self._manifest: ScrapeManifest | None = None
        self._completed_urls: set[str] = set()

    async def crawl(self) -> ScrapeManifest:
        """Run the full crawl operation.

        Returns:
            Manifest with crawl results.
        """
        # Initialize or load manifest
        await self._init_manifest()

        # Use progress bar unless quiet mode
        if self._config.quiet:
            return await self._crawl_without_progress()

        return await self._crawl_with_progress()

    async def _crawl_without_progress(self) -> ScrapeManifest:
        """Run crawl without progress bar (quiet mode)."""
        # Discover URLs
        if self._config.verbose:
            print(f"\n{'=' * 60}")
            print(f"Discovering URLs from {self._config.base_url}")
            print(f"{'=' * 60}\n")

        urls = await self._discover_urls()

        if not urls:
            print("No URLs found to crawl.")
            return self._manifest  # type: ignore

        # Filter out already completed URLs if resuming
        if self._config.resume and self._completed_urls:
            original_count = len(urls)
            urls = [u for u in urls if u.url not in self._completed_urls]
            if self._config.verbose:
                skipped = original_count - len(urls)
                print(f"Resuming: skipping {skipped} already crawled URLs")

        # Apply max_pages limit
        if self._config.max_pages > 0:
            urls = urls[: self._config.max_pages]

        self._manifest.total_urls = len(urls)  # type: ignore

        if self._config.verbose:
            print(f"\nWill crawl {len(urls)} URLs")
            print(f"{'=' * 60}\n")

        # Crawl URLs
        async for result in self._crawl_urls(urls):
            await self._process_result(result)

        # Finalize manifest
        self._manifest.completed_at = datetime.utcnow()  # type: ignore
        await self._storage.save_manifest(self._manifest, self._config.output_dir)  # type: ignore

        return self._manifest  # type: ignore

    async def _crawl_with_progress(self) -> ScrapeManifest:
        """Run crawl with Rich progress bar."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            # Discovery phase
            discovery_task = progress.add_task("[cyan]Discovering URLs...", total=None)

            if self._config.verbose:
                console.print(f"\n{'=' * 60}")
                console.print(f"Discovering URLs from {self._config.base_url}")
                console.print(f"{'=' * 60}\n")

            urls = await self._discover_urls()
            progress.remove_task(discovery_task)

            if not urls:
                console.print("[yellow]No URLs found to crawl.[/yellow]")
                return self._manifest  # type: ignore

            # Filter out already completed URLs if resuming
            if self._config.resume and self._completed_urls:
                original_count = len(urls)
                urls = [u for u in urls if u.url not in self._completed_urls]
                if self._config.verbose:
                    skipped = original_count - len(urls)
                    console.print(f"Resuming: skipping {skipped} already crawled URLs")

            # Apply max_pages limit
            if self._config.max_pages > 0:
                urls = urls[: self._config.max_pages]

            self._manifest.total_urls = len(urls)  # type: ignore

            if self._config.verbose:
                console.print(f"\nWill crawl {len(urls)} URLs")
                console.print(f"{'=' * 60}\n")

            # Crawl phase with progress bar
            crawl_task = progress.add_task(
                f"[green]Crawling {len(urls)} pages...",
                total=len(urls),
            )

            async for result in self._crawl_urls(urls, progress, crawl_task):
                await self._process_result(result)

        # Finalize manifest
        self._manifest.completed_at = datetime.utcnow()  # type: ignore
        await self._storage.save_manifest(self._manifest, self._config.output_dir)  # type: ignore

        return self._manifest  # type: ignore

    async def _init_manifest(self) -> None:
        """Initialize or load manifest."""
        if self._config.resume:
            existing = await self._storage.load_manifest(self._config.output_dir)
            if existing:
                self._manifest = existing
                self._completed_urls = self._storage.get_completed_urls(existing)
                if self._config.verbose:
                    print(f"Resuming from existing manifest ({len(self._completed_urls)} pages)")
                return

        # Create new manifest
        self._manifest = ScrapeManifest(
            platform=self._config.platform,
            base_url=self._config.base_url,
            output_dir=str(self._config.output_dir),
            started_at=datetime.utcnow(),
        )

    async def _discover_urls(self) -> list[DiscoveredUrl]:
        """Discover URLs to crawl."""
        strategy = self._adapter.get_discovery_strategy()

        if self._config.verbose:
            print(f"Using discovery strategy: {strategy.name}")

        urls: list[DiscoveredUrl] = []

        async for url in strategy.discover(self._config):
            # Apply adapter-level skip logic
            if self._adapter.should_skip(url.url):
                continue

            # Get priority from adapter
            url.priority = self._adapter.get_url_priority(url.url)
            urls.append(url)

        # Sort by priority (higher first)
        urls.sort(key=lambda u: (-u.priority, u.url))

        # If no URLs found, try fallback strategy
        if not urls and hasattr(self._adapter, "get_fallback_strategy"):
            fallback = self._adapter.get_fallback_strategy()
            if self._config.verbose:
                print(f"Primary strategy found no URLs, trying fallback: {fallback.name}")

            async for url in fallback.discover(self._config):
                if self._adapter.should_skip(url.url):
                    continue
                url.priority = self._adapter.get_url_priority(url.url)
                urls.append(url)

            urls.sort(key=lambda u: (-u.priority, u.url))

        return urls

    async def _crawl_urls(
        self,
        urls: list[DiscoveredUrl],
        progress: Progress | None = None,
        task_id: int | None = None,
    ) -> AsyncIterator[CrawlResult]:
        """Crawl a list of URLs.

        Args:
            urls: URLs to crawl.
            progress: Optional Rich progress bar.
            task_id: Optional task ID for progress updates.

        Yields:
            CrawlResult for each URL.
        """
        total = len(urls)

        async with httpx.AsyncClient(
            timeout=self._config.timeout,
            follow_redirects=True,
        ) as client:
            for i, discovered in enumerate(urls, 1):
                url = discovered.url
                start_time = time.time()

                # Update progress bar with truncated URL
                if progress is not None and task_id is not None:
                    truncated_url = self._truncate_url(url, max_len=50)
                    progress.update(
                        task_id,
                        description=f"[green]Crawling:[/green] {truncated_url}",
                    )

                if self._config.verbose:
                    print(f"[{i}/{total}] Crawling: {url}")

                try:
                    page = await self._fetch_and_extract(client, url)
                    duration = (time.time() - start_time) * 1000

                    yield CrawlResult(
                        url=url,
                        status=ScrapeStatus.SUCCESS,
                        page=page,
                        duration_ms=duration,
                    )

                except Exception as e:
                    duration = (time.time() - start_time) * 1000
                    error_msg = str(e)

                    if self._config.verbose:
                        print(f"  -> FAILED: {error_msg}")

                    yield CrawlResult(
                        url=url,
                        status=ScrapeStatus.FAILED,
                        error=error_msg,
                        duration_ms=duration,
                    )

                # Advance progress bar
                if progress is not None and task_id is not None:
                    progress.advance(task_id)

                # Rate limiting
                await asyncio.sleep(self._config.request_delay)

    def _truncate_url(self, url: str, max_len: int = 50) -> str:
        """Truncate URL for display in progress bar."""
        if len(url) <= max_len:
            return url
        # Keep the last part of the URL (path)
        return "..." + url[-(max_len - 3) :]

    async def _fetch_and_extract(self, client: httpx.AsyncClient, url: str) -> DocumentPage:
        """Fetch a URL and extract content.

        Args:
            client: HTTP client.
            url: URL to fetch.

        Returns:
            Extracted DocumentPage.
        """
        # Retry logic
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()

                html = response.text
                page = self._adapter.extract_content(html, url)

                # Set filepath
                page.filepath = self._adapter.url_to_filepath(url, self._config.output_dir)

                return page

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise  # Don't retry 404s
                last_error = e

            except httpx.RequestError as e:
                last_error = e

            if attempt < self._config.max_retries - 1:
                await asyncio.sleep(self._config.request_delay * (attempt + 1))

        raise last_error or Exception("Unknown error during fetch")

    async def _process_result(self, result: CrawlResult) -> None:
        """Process a crawl result.

        Args:
            result: Result to process.
        """
        if result.status == ScrapeStatus.SUCCESS and result.page:
            # Save the page
            await self._storage.save_page(result.page, result.page.filepath)  # type: ignore

            # Update manifest
            self._manifest.successful += 1  # type: ignore
            self._manifest.pages.append(  # type: ignore
                {
                    "url": result.url,
                    "filepath": str(result.page.filepath),
                    "title": result.page.title,
                    "word_count": result.page.word_count,
                    "scraped_at": result.page.scraped_at.isoformat(),
                }
            )

            if self._config.verbose:
                print(f"  -> Saved: {result.page.filepath}")

        else:
            self._manifest.failed += 1  # type: ignore
            self._manifest.failed_urls.append(  # type: ignore
                {
                    "url": result.url,
                    "error": result.error,
                }
            )

        # Periodically save manifest for resume support
        if (self._manifest.successful + self._manifest.failed) % 10 == 0:  # type: ignore
            await self._storage.save_manifest(
                self._manifest,
                self._config.output_dir,  # type: ignore
            )
