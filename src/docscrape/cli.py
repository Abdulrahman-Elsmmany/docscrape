"""Simplified CLI for docscrape with smart defaults."""

import asyncio
import re
import sys
from pathlib import Path
from typing import Annotated, Optional
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from docscrape import __version__
from docscrape.adapters.factory import PlatformAdapterFactory
from docscrape.core.models import ScrapeConfig
from docscrape.engine.crawler import DocumentationCrawler
from docscrape.storage.filesystem import FilesystemStorage

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold]docscrape[/bold] version {__version__}")
        raise typer.Exit()


def _derive_output_from_url(url: str) -> Path:
    """Derive output directory from URL.

    Examples:
        https://docs.pipecat.ai -> ./pipecat/
        https://docs.livekit.io/agents -> ./livekit/
        https://example.com/docs -> ./example/
    """
    parsed = urlparse(url)
    domain = parsed.netloc

    # Remove common prefixes
    for prefix in ["docs.", "www.", "developer.", "developers."]:
        if domain.startswith(prefix):
            domain = domain[len(prefix) :]

    # Extract the main domain name (before .com, .io, .ai, etc.)
    match = re.match(r"^([a-zA-Z0-9-]+)", domain)
    if match:
        name = match.group(1).lower()
    else:
        name = "docs"

    return Path(f"./{name}/")


async def _run_crawler(adapter, config: ScrapeConfig) -> None:
    """Run the crawler asynchronously."""
    storage = FilesystemStorage()
    crawler = DocumentationCrawler(adapter, storage, config)

    # Display header
    console.print()
    console.print(
        Panel(
            f"[bold cyan]Platform:[/bold cyan] {config.platform}\n"
            f"[bold green]URL:[/bold green] {config.base_url}\n"
            f"[bold yellow]Output:[/bold yellow] {config.output_dir}",
            title="[bold]docscrape[/bold]",
            border_style="blue",
        )
    )

    if config.resume:
        console.print("[dim]Resuming from previous scrape...[/dim]")

    console.print()

    try:
        manifest = await crawler.crawl()

        # Print summary
        console.print()
        console.print(
            Panel(
                f"[bold green]Successful:[/bold green] {manifest.successful}\n"
                f"[bold red]Failed:[/bold red] {manifest.failed}\n"
                f"[bold yellow]Output:[/bold yellow] {config.output_dir}",
                title="[bold green]Scrape Complete![/bold green]",
                border_style="green",
            )
        )

        if manifest.failed_urls:
            console.print()
            console.print("[yellow]Failed URLs:[/yellow]")
            for failed in manifest.failed_urls[:5]:
                console.print(f"  [dim]•[/dim] {failed['url']}")
            if len(manifest.failed_urls) > 5:
                console.print(f"  [dim]... and {len(manifest.failed_urls) - 5} more[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Progress saved for resume.[/yellow]")
        raise typer.Exit(1)

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)


def _scrape(
    url: str,
    output: Optional[Path],
    max_pages: int,
    delay: float,
    resume: bool,
    verbose: bool,
    quiet: bool,
    include: Optional[list[str]],
    exclude: Optional[list[str]],
) -> None:
    """Execute the scrape operation."""
    # Validate URL
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Auto-detect output directory if not specified
    if output is None:
        output = _derive_output_from_url(url)

    # Get adapter (auto-detect platform or use generic)
    adapter = PlatformAdapterFactory.get_adapter(url=url)

    # Create config
    config = ScrapeConfig(
        output_dir=output,
        base_url=url,
        platform=adapter.name,
        max_pages=max_pages,
        request_delay=delay,
        resume=resume,
        verbose=verbose,
        quiet=quiet,
        include_patterns=include or [],
        exclude_patterns=exclude or [],
    )

    # Run crawler
    asyncio.run(_run_crawler(adapter, config))


def _list_platforms() -> None:
    """List available optimized platform adapters."""
    platforms = PlatformAdapterFactory.list_platforms()

    table = Table(
        title="[bold]Optimized Platform Adapters[/bold]",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Platform", style="cyan")
    table.add_column("Base URL", style="green")
    table.add_column("Discovery", style="yellow")

    for platform in platforms:
        adapter = PlatformAdapterFactory.get_adapter(platform=platform)
        strategy = adapter.get_discovery_strategy()
        table.add_row(platform, adapter.base_url, strategy.name)

    console.print()
    console.print(table)
    console.print()
    console.print(
        "[dim]Note: Any documentation site works! These platforms have optimized adapters.[/dim]"
    )


app = typer.Typer(
    name="docscrape",
    help="Scrape any documentation site to Markdown in seconds.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command()
def scrape(
    url: Annotated[
        str,
        typer.Argument(
            help="Documentation URL to scrape (e.g., https://docs.pipecat.ai)"
        ),
    ],
    output: Annotated[
        Optional[Path],
        typer.Option(
            "-o",
            "--output",
            help="Output directory [default: auto-detected from URL]",
        ),
    ] = None,
    max_pages: Annotated[
        int,
        typer.Option(
            "-m",
            "--max-pages",
            help="Maximum pages to scrape (0 = unlimited)",
        ),
    ] = 0,
    delay: Annotated[
        float,
        typer.Option(
            "-d",
            "--delay",
            help="Delay between requests in seconds",
        ),
    ] = 0.5,
    resume: Annotated[
        bool,
        typer.Option(
            "-r",
            "--resume",
            help="Resume from previous scrape",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "-v",
            "--verbose",
            help="Verbose output",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "-q",
            "--quiet",
            help="Suppress progress bar (for scripting/CI)",
        ),
    ] = False,
    include: Annotated[
        Optional[list[str]],
        typer.Option(
            "-i",
            "--include",
            help="URL patterns to include (regex)",
        ),
    ] = None,
    exclude: Annotated[
        Optional[list[str]],
        typer.Option(
            "-e",
            "--exclude",
            help="URL patterns to exclude (regex)",
        ),
    ] = None,
) -> None:
    """Scrape a documentation site to Markdown.

    \b
    Examples:
        docscrape scrape https://docs.pipecat.ai
        docscrape scrape https://docs.livekit.io -o ./livekit-docs
        docscrape scrape https://docs.example.com -m 50 -v
    """
    _scrape(url, output, max_pages, delay, resume, verbose, quiet, include, exclude)


@app.command("platforms")
def platforms() -> None:
    """List available optimized platform adapters."""
    _list_platforms()


# Create a simpler CLI for direct URL usage
def main() -> None:
    """Main entry point with smart argument handling.

    Allows both:
        docscrape https://docs.example.com
        docscrape scrape https://docs.example.com
    """
    # Check if first arg looks like a URL (not a command)
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        # If it looks like a URL or starts with http, insert 'scrape' command
        if (
            first_arg.startswith(("http://", "https://"))
            or "." in first_arg
            and first_arg not in ("platforms", "scrape", "--help", "-h", "--version", "-V")
        ):
            sys.argv.insert(1, "scrape")

    app()


if __name__ == "__main__":
    main()
