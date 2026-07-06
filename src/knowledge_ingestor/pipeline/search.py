from __future__ import annotations

import math

from ..ai import build_provider
from ..config import Config
from ..exceptions import AIError
from ..models import Document
from ..storage import StorageBackend


async def semantic_search(
    query: str, storage: StorageBackend, config: Config
) -> list[tuple[Document, float]]:
    """Rank stored Documents by embedding similarity to query, highest first.

    Requires an AI provider (config.ai_provider) and documents previously
    enriched with an embedding (see run_enrich_stage).
    """
    provider = build_provider(config)
    if provider is None:
        raise AIError("semantic search requires an AI provider (config.ai_provider)")

    try:
        query_embedding = (await provider.embed([query]))[0]
    finally:
        aclose = getattr(provider, "aclose", None)
        if aclose is not None:
            await aclose()

    # "" matches every document under every StorageBackend's substring search,
    # so this doubles as "list all documents" without extending the contract.
    documents = await storage.search("")
    scored = [
        (document, _cosine_similarity(query_embedding, document.embedding))
        for document in documents
        if document.embedding
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
