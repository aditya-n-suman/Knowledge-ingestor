import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .. import __version__
from ..config import Config
from ..core.session import close_client
from ..logger import configure_logging
from ..pipeline import run_fetch_stage

app = typer.Typer()
console = Console()


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
