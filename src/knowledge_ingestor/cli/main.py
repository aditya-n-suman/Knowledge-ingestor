import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .. import __version__
from ..config import Config
from ..core.session import close_client
from ..logger import configure_logging
from ..pipeline import run_extract_stage, run_fetch_stage

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

    async def _run() -> None:
        try:
            fetch_results = await run_fetch_stage(all_urls, config)
        finally:
            await close_client()
        return run_extract_stage(fetch_results)

    documents = asyncio.run(_run())

    config.output_dir.mkdir(parents=True, exist_ok=True)
    table = Table()
    table.add_column("Title")
    table.add_column("URL")
    table.add_column("Words")
    table.add_column("Extractor")
    for document in documents:
        (config.output_dir / f"{document.id}.md").write_text(
            document.content, encoding="utf-8"
        )
        table.add_row(
            document.title,
            document.url,
            str(len(document.content.split())),
            document.metadata.get("extractor", ""),
        )
    console.print(table)
