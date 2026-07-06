import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .. import __version__
from ..ai import build_provider
from ..config import Config
from ..core.session import close_client
from ..logger import configure_logging
from ..models import Document
from ..pipeline import (
    discover_urls,
    run_enrich_stage,
    run_fetch_stage,
    run_ingest_stage,
    semantic_search,
)
from ..storage import build_storage

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


async def _extract_links_with_ai(text: str, config: Config) -> list[str]:
    """Use the configured AI provider to pull URLs out of arbitrary,
    unstructured text (labels, prose, timestamps, ...) instead of assuming
    one-clean-URL-per-line."""
    provider = build_provider(config)
    if provider is None:
        console.print(
            "[red]--extract-links requires an AI provider "
            "(set ai_provider in knowledge.yaml).[/red]"
        )
        raise typer.Exit(code=1)
    try:
        return await provider.extract_links(text)
    finally:
        aclose = getattr(provider, "aclose", None)
        if aclose is not None:
            await aclose()


async def _resolve_input_urls(
    urls: list[str] | None, file: Path | None, extract_links: bool, config: Config
) -> list[str]:
    all_urls = list(urls or [])
    if file is not None:
        text = file.read_text(encoding="utf-8")
        if extract_links:
            all_urls.extend(await _extract_links_with_ai(text, config))
        else:
            all_urls.extend(
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.strip().startswith("#")
            )
    if not all_urls:
        console.print("[red]No URLs found. Pass URLs as arguments or use --file.[/red]")
        raise typer.Exit(code=1)
    return all_urls


def _apply_overrides(
    config: Config,
    *,
    min_delay: float | None = None,
    max_delay: float | None = None,
    depth: int | None = None,
    max_pages: int | None = None,
) -> None:
    if min_delay is not None:
        config.min_request_delay = min_delay
    if max_delay is not None:
        config.max_request_delay = max_delay
    if depth is not None:
        config.max_depth = depth
    if max_pages is not None:
        config.max_pages = max_pages


async def _persist_documents(documents: list[Document], config: Config) -> None:
    storage = build_storage(config)
    for document in documents:
        await storage.save(document)


def _print_documents_table(documents: list[Document]) -> None:
    table = Table()
    table.add_column("Title")
    table.add_column("URL")
    table.add_column("Words")
    table.add_column("Source")
    for document in documents:
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
    min_delay: float = typer.Option(
        None,
        "--min-delay",
        help="Min random delay (seconds) between requests to the same host",
    ),
    max_delay: float = typer.Option(
        None,
        "--max-delay",
        help="Max random delay (seconds) between requests to the same host",
    ),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True),
) -> None:
    """Resolve and download one or more URLs, caching the raw HTML."""
    configure_logging(verbose)
    all_urls = _collect_urls(urls, file)
    config = Config.load()
    _apply_overrides(config, min_delay=min_delay, max_delay=max_delay)

    async def _run() -> None:
        try:
            results = await run_fetch_stage(all_urls, config)
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
    extract_links: bool = typer.Option(
        False,
        "--extract-links",
        help="Use config.ai_provider to pull URLs out of --file instead of "
        "parsing it as one-URL-per-line",
    ),
    enrich: bool = typer.Option(
        False,
        "--enrich",
        help="Generate summary/flashcards/embedding via config.ai_provider",
    ),
    min_delay: float = typer.Option(
        None,
        "--min-delay",
        help="Min random delay (seconds) between requests to the same host",
    ),
    max_delay: float = typer.Option(
        None,
        "--max-delay",
        help="Max random delay (seconds) between requests to the same host",
    ),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True),
) -> None:
    """Fetch, extract, and store one or more URLs as Documents."""
    configure_logging(verbose)
    config = Config.load()
    _apply_overrides(config, min_delay=min_delay, max_delay=max_delay)

    async def _run() -> list[Document]:
        try:
            all_urls = await _resolve_input_urls(urls, file, extract_links, config)
            documents = await run_ingest_stage(all_urls, config)
            if enrich:
                documents = await run_enrich_stage(documents, config)
            await _persist_documents(documents, config)
            return documents
        finally:
            await close_client()

    documents = asyncio.run(_run())
    _print_documents_table(documents)


@app.command()
def crawl(
    seed_url: str = typer.Argument(..., help="Seed URL to discover pages from"),
    depth: int = typer.Option(None, "--depth", help="Max link-traversal depth"),
    max_pages: int = typer.Option(None, "--max-pages", help="Max pages to ingest"),
    enrich: bool = typer.Option(
        False,
        "--enrich",
        help="Generate summary/flashcards/embedding via config.ai_provider",
    ),
    min_delay: float = typer.Option(
        None,
        "--min-delay",
        help="Min random delay (seconds) between requests to the same host",
    ),
    max_delay: float = typer.Option(
        None,
        "--max-delay",
        help="Max random delay (seconds) between requests to the same host",
    ),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True),
) -> None:
    """Discover pages from a seed URL (sitemap.xml or link traversal) and ingest each one."""
    configure_logging(verbose)
    config = Config.load()
    _apply_overrides(
        config,
        min_delay=min_delay,
        max_delay=max_delay,
        depth=depth,
        max_pages=max_pages,
    )

    async def _run() -> list[Document]:
        try:
            urls = await discover_urls(seed_url, config)
            console.print(f"Discovered {len(urls)} page(s)")
            documents = await run_ingest_stage(urls, config)
            if enrich:
                documents = await run_enrich_stage(documents, config)
            await _persist_documents(documents, config)
            return documents
        finally:
            await close_client()

    documents = asyncio.run(_run())
    _print_documents_table(documents)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    semantic: bool = typer.Option(
        False,
        "--semantic",
        help="Rank by embedding similarity (requires config.ai_provider)",
    ),
    limit: int = typer.Option(10, "--limit", help="Max results to show"),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True),
) -> None:
    """Search stored Documents by substring, or by embedding similarity with --semantic."""
    configure_logging(verbose)
    config = Config.load()
    storage = build_storage(config)

    async def _run() -> list[tuple[Document, float | None]]:
        if semantic:
            return await semantic_search(query, storage, config)
        return [(document, None) for document in await storage.search(query)]

    results = asyncio.run(_run())

    table = Table()
    table.add_column("Title")
    table.add_column("URL")
    if semantic:
        table.add_column("Score")
    for document, score in results[:limit]:
        row = [document.title, document.url]
        if semantic:
            row.append(f"{score:.3f}")
        table.add_row(*row)
    console.print(table)
