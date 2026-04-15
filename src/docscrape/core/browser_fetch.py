"""Headless-browser fetch helper backed by crawl4ai / Playwright.

Used as a fallback when the curl_cffi path is blocked by anti-bot,
rate limits, or when the page content is JavaScript-rendered and the
static HTML is empty.
"""

from __future__ import annotations

from dataclasses import dataclass

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


@dataclass
class RenderedResponse:
    """Minimal response from a rendered fetch."""

    html: str
    final_url: str
    success: bool
    status_code: int | None = None
    error: str | None = None


_browser_singleton: AsyncWebCrawler | None = None


async def get_browser() -> AsyncWebCrawler:
    """Return a shared headless crawler instance, starting it lazily."""
    global _browser_singleton
    if _browser_singleton is None:
        crawler = AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False))
        await crawler.start()
        _browser_singleton = crawler
    return _browser_singleton


async def close_browser() -> None:
    """Shut down the shared crawler (call once at end of run)."""
    global _browser_singleton
    if _browser_singleton is not None:
        await _browser_singleton.close()
        _browser_singleton = None


async def fetch_rendered(url: str, timeout: float = 60.0) -> RenderedResponse:
    """Fetch a URL using a real browser (Playwright via crawl4ai)."""
    crawler = await get_browser()
    cfg = CrawlerRunConfig(
        page_timeout=int(timeout * 1000),
        verbose=False,
        remove_overlay_elements=True,
    )
    try:
        result = await crawler.arun(url=url, config=cfg)
    except Exception as e:  # noqa: BLE001
        return RenderedResponse(html="", final_url=url, success=False, error=str(e))

    html = result.html or ""
    final_url = getattr(result, "url", None) or url
    status = getattr(result, "status_code", None)
    return RenderedResponse(
        html=html,
        final_url=str(final_url),
        success=bool(result.success) and len(html) > 0,
        status_code=status,
        error=getattr(result, "error_message", None),
    )
