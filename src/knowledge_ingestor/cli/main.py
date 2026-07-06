import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .. import __version__
from ..config import Config
from ..core.session import close_client
from ..logger import configure_logging
from ..models import Document
from ..pipeline import discover_urls, run_fetch_stage, run_ingest_stage

app = typer.Typer()
console = Console()


def _collect_urls(urls: list[str] | None, file: Path | None) -> list[str]:
    all_urls = list(urls or [])
    if file is not None:
        lines = file.read_text(encoding="utf-8").splitlines()
        all_urls.extend(
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        )
    if not all_urls:
        console.print(
            "[red]No URLs provided. Pass URLs as arguments or use --file.[/red]"
        )
        raise typer.Exit(code=1)
    return all_urls


def _write_documents(documents: list[Document], config: Config) -> None:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    table = Table()
    table.add_column("Title")
    table.add_column("URL")
    table.add_column("Words")
    table.add_column("Source")
    for document in documents:
        (config.output_dir / f"{document.id}.md").write_text(
            document.content, encoding="utf-8"
        )
        table.add_row(
            document.title,
            document.url,
            str(len(document.content.split())),
            document.metadata.get("source", ""),
        )
    console.print(table)


@app.command()
def version() -> None:
    console.print(f"Knowledge Ingestor v{__version__}")


@app.command()
def fetch(
    urls: list[str] = typer.Argument(None, help="URLs to fetch"),
    file: Path = typer.Option(None, "--file", "-f", help="File with one URL per line"),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True),
) -> None:
    """Resolve and download one or more URLs, caching the raw HTML."""
    configure_logging(verbose)
    all_urls = _collect_urls(urls, file)

    async def _run() -> None:
        try:
            results = await run_fetch_stage(all_urls, Config.load())
        finally:
            await close_client()

        table = Table()
        table.add_column("URL")
        table.add_column("Resolved")
        table.add_column("Status")
        table.add_column("Cached")
        for result in results:
            table.add_row(
                result.url,
                result.resolved_url,
                str(result.status_code),
                "yes" if result.from_cache else "no",
            )
        console.print(table)

    asyncio.run(_run())


@app.command()
def ingest(
    urls: list[str] = typer.Argument(None, help="URLs to ingest"),
    file: Path = typer.Option(None, "--file", "-f", help="File with one URL per line"),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True),
) -> None:
    """Fetch and extract one or more URLs into Markdown documents."""
    configure_logging(verbose)
    all_urls = _collect_urls(urls, file)
    config = Config.load()

    async def _run() -> list:
        try:
            return await run_ingest_stage(all_urls, config)
        finally:
            await close_client()

    documents = asyncio.run(_run())
    _write_documents(documents, config)


@app.command()
def crawl(
    seed_url: str = typer.Argument(..., help="Seed URL to discover pages from"),
    depth: int = typer.Option(None, "--depth", help="Max link-traversal depth"),
    max_pages: int = typer.Option(None, "--max-pages", help="Max pages to ingest"),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True),
) -> None:
    """Discover pages from a seed URL (sitemap.xml or link traversal) and ingest each one."""
    configure_logging(verbose)
    config = Config.load()
    if depth is not None:
        config.max_depth = depth
    if max_pages is not None:
        config.max_pages = max_pages

    async def _run() -> list[Document]:
        try:
            urls = await discover_urls(seed_url, config)
            console.print(f"Discovered {len(urls)} page(s)")
            return await run_ingest_stage(urls, config)
        finally:
            await close_client()

    documents = asyncio.run(_run())
    _write_documents(documents, config)
