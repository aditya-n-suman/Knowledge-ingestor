import logging

from rich.logging import RichHandler

logger = logging.getLogger("knowledge_ingestor")


def configure_logging(verbosity: int = 0) -> None:
    """Configure structured logging. verbosity: 0=WARNING, 1=INFO, 2+=DEBUG."""
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logger.handlers.clear()
    handler = RichHandler(rich_tracebacks=True, show_path=verbosity >= 2)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
