from __future__ import annotations

from ..ai import build_provider
from ..config import Config
from ..exceptions import AIError
from ..logger import logger
from ..models import Document


async def run_enrich_stage(
    documents: list[Document], config: Config | None = None
) -> list[Document]:
    """Populate summary, flashcards, and embedding on each Document via the
    configured AI provider. A no-op when none is configured (AI stays optional)."""
    config = config or Config()
    provider = build_provider(config)
    if provider is None:
        return documents

    try:
        for document in documents:
            try:
                document.summary = await provider.summarize(document.content)
                document.flashcards = await provider.generate_flashcards(
                    document.content
                )
                document.embedding = (await provider.embed([document.content]))[0]
            except AIError:
                logger.exception("failed to enrich document %s", document.id)
    finally:
        aclose = getattr(provider, "aclose", None)
        if aclose is not None:
            await aclose()
    return documents
