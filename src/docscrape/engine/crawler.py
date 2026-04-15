"""Streaming documentation crawler with live discovery + crawl dashboard.

Runs every discovery strategy returned by the adapter concurrently,
dedupes their output, and feeds URLs into the crawl queue as soon as
they're found. The live Rich dashboard shows per-strategy discovery
state, per-worker in-flight URLs, and the most recent failure reason.
"""

import asyncio
import random
import time
from datetime import datetime
from email.utils import parsedate_to_datetime

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from docscrape.core.browser_fetch import RenderedResponse, close_browser, fetch_rendered
from docscrape.core.http import DocAsyncSession, HTTPError, RequestException, make_session
from docscrape.core.interfaces import DiscoveryStrategy, PlatformAdapter, StorageBackend
from docscrape.core.models import (
    CrawlResult,
    DiscoveredUrl,
    DocumentPage,
    ScrapeConfig,
    ScrapeManifest,
    ScrapeStatus,
)

console = Console()

_MAX_CONCURRENCY = 5
_SENTINEL: DiscoveredUrl | None = None


class DocumentationCrawler:
    """Streaming crawler that overlaps discovery with fetching."""

    def __init__(
        self,
        adapter: PlatformAdapter,
        storage: StorageBackend,
        config: ScrapeConfig,
    ) -> None:
        self._adapter = adapter
        self._storage = storage
        self._config = config
        self._manifest: ScrapeManifest | None = None
        self._completed_urls: set[str] = set()

    async def crawl(self) -> ScrapeManifest:
        await self._init_manifest()
        try:
            return await self._run_pipeline()
        finally:
            await close_browser()

    async def _init_manifest(self) -> None:
        if self._config.resume:
            existing = await self._storage.load_manifest(self._config.output_dir)
            if existing:
                self._manifest = existing
                self._completed_urls = self._storage.get_completed_urls(existing)
                return
        self._manifest = ScrapeManifest(
            platform=self._config.platform,
            base_url=self._config.base_url,
            output_dir=str(self._config.output_dir),
            started_at=datetime.utcnow(),
        )

    async def _run_pipeline(self) -> ScrapeManifest:
        assert self._manifest is not None

        strategies = self._get_strategies()
        discovery_state: dict = {
            "strategies": {s.name: "running" for s in strategies},
            "seen": set(),
            "found": 0,
            "enqueued": 0,
            "current_depth": 0,
        }
        crawl_state: dict = {
            "ok": 0,
            "fail": 0,
            "in_flight": {},
            "last_error": None,
            "completed": 0,
            "workers": {i: "" for i in range(_MAX_CONCURRENCY)},
        }

        url_queue: asyncio.Queue[DiscoveredUrl | None] = asyncio.Queue(maxsize=200)

        async with make_session(timeout=self._config.timeout) as crawl_client:
            ui_stop = asyncio.Event()
            ui_task = asyncio.create_task(
                self._render_dashboard(discovery_state, crawl_state, ui_stop)
            )

            discovery_task = asyncio.create_task(
                self._run_discovery(strategies, url_queue, discovery_state)
            )

            worker_tasks = [
                asyncio.create_task(
                    self._crawl_worker(
                        worker_id=i,
                        client=crawl_client,
                        url_queue=url_queue,
                        discovery_state=discovery_state,
                        crawl_state=crawl_state,
                    )
                )
                for i in range(_MAX_CONCURRENCY)
            ]

            await discovery_task

            # Signal workers to stop once the queue is drained.
            for _ in range(_MAX_CONCURRENCY):
                await url_queue.put(_SENTINEL)

            await asyncio.gather(*worker_tasks)

            ui_stop.set()
            await ui_task

        self._manifest.completed_at = datetime.utcnow()
        await self._storage.save_manifest(self._manifest, self._config.output_dir)
        return self._manifest

    def _get_strategies(self) -> list[DiscoveryStrategy]:
        if hasattr(self._adapter, "get_discovery_strategies"):
            return list(self._adapter.get_discovery_strategies())
        return [self._adapter.get_discovery_strategy()]

    # ------------------------------------------------------------------ discovery

    async def _run_discovery(
        self,
        strategies: list[DiscoveryStrategy],
        url_queue: asyncio.Queue[DiscoveredUrl | None],
        state: dict,
    ) -> None:
        """Fan out every strategy, merge results into the crawl queue."""
        tasks = [
            asyncio.create_task(self._run_single_strategy(s, url_queue, state))
            for s in strategies
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_single_strategy(
        self,
        strategy: DiscoveryStrategy,
        url_queue: asyncio.Queue[DiscoveredUrl | None],
        state: dict,
    ) -> None:
        try:
            async for discovered in strategy.discover(self._config):
                key = _dedup_key(discovered.url)
                if key in state["seen"]:
                    continue
                state["seen"].add(key)
                state["found"] += 1

                if self._adapter.should_skip(discovered.url):
                    continue
                if self._config.resume and discovered.url in self._completed_urls:
                    continue
                if (
                    self._config.max_pages > 0
                    and state["enqueued"] >= self._config.max_pages
                ):
                    state["strategies"][strategy.name] = "stopped (max_pages)"
                    return

                discovered.priority = self._adapter.get_url_priority(discovered.url)
                state["enqueued"] += 1
                await url_queue.put(discovered)
            state["strategies"][strategy.name] = "done"
        except Exception as e:  # noqa: BLE001
            state["strategies"][strategy.name] = f"error: {type(e).__name__}"
            if self._config.verbose:
                console.print(f"[red]{strategy.name} failed: {e}[/red]")

    # ------------------------------------------------------------------ crawl

    async def _crawl_worker(
        self,
        worker_id: int,
        client: DocAsyncSession,
        url_queue: asyncio.Queue[DiscoveredUrl | None],
        discovery_state: dict,
        crawl_state: dict,
    ) -> None:
        assert self._manifest is not None
        while True:
            item = await url_queue.get()
            if item is _SENTINEL:
                crawl_state["workers"][worker_id] = ""
                return

            if (
                self._config.max_pages > 0
                and crawl_state["completed"] >= self._config.max_pages
            ):
                crawl_state["workers"][worker_id] = ""
                continue

            url = item.url
            crawl_state["workers"][worker_id] = url
            start = time.time()
            try:
                page = await self._fetch_and_extract(client, url)
                duration = (time.time() - start) * 1000
                result = CrawlResult(
                    url=url,
                    status=ScrapeStatus.SUCCESS,
                    page=page,
                    duration_ms=duration,
                )
            except Exception as e:  # noqa: BLE001
                duration = (time.time() - start) * 1000
                result = CrawlResult(
                    url=url,
                    status=ScrapeStatus.FAILED,
                    error=_short_error(e),
                    duration_ms=duration,
                )
                crawl_state["last_error"] = f"{url} :: {result.error}"

            await self._process_result(result, crawl_state)
            crawl_state["completed"] += 1
            await asyncio.sleep(self._config.request_delay)

    async def _fetch_and_extract(
        self,
        client: DocAsyncSession,
        url: str,
    ) -> DocumentPage:
        """Fetch a URL via curl_cffi with backoff; fall back to a browser."""
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries):
            try:
                response = await client.get(url)

                if response.status_code in (429, 503):
                    wait = _parse_retry_after(
                        response.headers.get("retry-after"),
                        default=min(60.0, 2.0 * (2**attempt)) + random.random(),
                    )
                    await asyncio.sleep(wait)
                    last_error = HTTPError(
                        f"{response.status_code} {_reason(response)}"
                    )
                    continue

                response.raise_for_status()  # type: ignore[no-untyped-call]

                page = self._adapter.extract_content(response.text, url)
                if len(page.content_markdown) < 200:
                    # Empty/JS-rendered — try browser
                    rendered = await self._try_rendered(url)
                    if rendered is not None:
                        page = rendered

                page.filepath = self._adapter.url_to_filepath(
                    url, self._config.output_dir
                )
                return page

            except HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    raise
                last_error = e
            except RequestException as e:
                last_error = e

            if attempt < self._config.max_retries - 1:
                await asyncio.sleep(
                    min(60.0, self._config.request_delay * (2**attempt))
                    + random.random()
                )

        # All HTTP retries exhausted — try the browser fallback once.
        rendered_page = await self._try_rendered(url)
        if rendered_page is not None:
            rendered_page.filepath = self._adapter.url_to_filepath(
                url, self._config.output_dir
            )
            return rendered_page

        raise last_error or Exception("Unknown error during fetch")

    async def _try_rendered(self, url: str) -> DocumentPage | None:
        try:
            rendered: RenderedResponse = await fetch_rendered(
                url, timeout=self._config.timeout * 2
            )
        except Exception:  # noqa: BLE001
            return None
        if not rendered.success or not rendered.html:
            return None
        try:
            page = self._adapter.extract_content(rendered.html, url)
        except Exception:  # noqa: BLE001
            return None
        if len(page.content_markdown) < 200:
            return None
        return page

    async def _process_result(self, result: CrawlResult, crawl_state: dict) -> None:
        assert self._manifest is not None
        if result.status == ScrapeStatus.SUCCESS and result.page:
            await self._storage.save_page(result.page, result.page.filepath)  # type: ignore
            self._manifest.successful += 1
            crawl_state["ok"] += 1
            self._manifest.pages.append(
                {
                    "url": result.url,
                    "filepath": str(result.page.filepath),
                    "title": result.page.title,
                    "word_count": result.page.word_count,
                    "scraped_at": result.page.scraped_at.isoformat(),
                }
            )
        else:
            self._manifest.failed += 1
            crawl_state["fail"] += 1
            self._manifest.failed_urls.append(
                {"url": result.url, "error": result.error}
            )

        total = self._manifest.successful + self._manifest.failed
        if total % 10 == 0:
            await self._storage.save_manifest(
                self._manifest, self._config.output_dir
            )

    # ------------------------------------------------------------------ UI

    async def _render_dashboard(
        self,
        discovery_state: dict,
        crawl_state: dict,
        stop: asyncio.Event,
    ) -> None:
        if self._config.quiet:
            await stop.wait()
            return

        with Live(
            self._build_dashboard(discovery_state, crawl_state),
            console=console,
            refresh_per_second=4,
            transient=False,
        ) as live:
            while not stop.is_set():
                live.update(self._build_dashboard(discovery_state, crawl_state))
                try:
                    await asyncio.wait_for(stop.wait(), timeout=0.25)
                except asyncio.TimeoutError:
                    pass
            live.update(self._build_dashboard(discovery_state, crawl_state))

    def _build_dashboard(self, discovery_state: dict, crawl_state: dict):
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="right", style="bold cyan")
        table.add_column()

        strategies_line = Text()
        for name, status in discovery_state["strategies"].items():
            color = {
                "running": "yellow",
                "done": "green",
                "stopped (max_pages)": "green",
            }.get(status, "red")
            strategies_line.append(f"{name}:{status}  ", style=color)

        table.add_row(
            "Discovery",
            Text.assemble(
                (f"{discovery_state['found']} found ", "bold white"),
                (f"{discovery_state['enqueued']} queued  ", "dim"),
                strategies_line,
            ),
        )

        ok = crawl_state["ok"]
        fail = crawl_state["fail"]
        completed = crawl_state["completed"]
        total_queued = discovery_state["enqueued"]
        crawl_summary = Text()
        crawl_summary.append(
            f"{completed}/{total_queued}  ", style="bold white"
        )
        crawl_summary.append(f"ok={ok} ", style="green")
        crawl_summary.append(f"fail={fail}", style="red" if fail else "dim")
        table.add_row("Crawl", crawl_summary)

        active = [u for u in crawl_state["workers"].values() if u]
        if active:
            workers = Text()
            for u in active[:_MAX_CONCURRENCY]:
                workers.append(f"  • {_truncate(u, 80)}\n", style="dim")
            table.add_row("In flight", workers)

        last_error = crawl_state.get("last_error")
        if last_error:
            table.add_row("Last error", Text(_truncate(last_error, 120), style="red"))

        return Panel(
            Group(table),
            title="[bold]docscrape[/bold]",
            border_style="blue",
        )


def _dedup_key(u: str) -> str:
    return u.rstrip("/")


def _short_error(err: Exception) -> str:
    msg = str(err)
    if not msg:
        msg = type(err).__name__
    return msg[:240]


def _reason(response) -> str:
    return getattr(response, "reason", "") or ""


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return "..." + text[-(max_len - 3) :]


def _parse_retry_after(header_value: str | None, default: float) -> float:
    if not header_value:
        return default
    v = header_value.strip()
    if v.isdigit():
        return min(120.0, float(v))
    try:
        dt = parsedate_to_datetime(v)
    except (TypeError, ValueError):
        return default
    if dt is None:
        return default
    from datetime import datetime, timezone

    now = datetime.now(tz=timezone.utc)
    delta = (dt - now).total_seconds()
    return max(0.0, min(120.0, delta)) if delta > 0 else default


__all__ = ["DocumentationCrawler"]
