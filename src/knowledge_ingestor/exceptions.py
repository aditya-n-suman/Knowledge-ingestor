class IngestorError(Exception):
    """Base error for all Knowledge Ingestor failures."""


class DownloadError(IngestorError):
    """Raised when a URL cannot be fetched after exhausting retries."""


class ExtractionError(IngestorError):
    """Raised when content cannot be extracted from a fetched document."""


class PluginError(IngestorError):
    """Raised when a plugin fails to handle a source it claimed to support."""


class StorageError(IngestorError):
    """Raised when a storage backend fails to save, load, delete, or search."""


class AIError(IngestorError):
    """Raised when an AI provider fails to summarize, generate, or embed."""
