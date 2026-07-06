from pathlib import Path


class FilesystemPaths:
    """Shared file-path conventions for file-based storage backends."""

    def __init__(self, directory: Path, suffix: str):
        self.directory = directory
        self.suffix = suffix
        self.directory.mkdir(parents=True, exist_ok=True)

    def path_for(self, document_id: str) -> Path:
        return self.directory / f"{document_id}{self.suffix}"

    def all_paths(self) -> list[Path]:
        return sorted(self.directory.glob(f"*{self.suffix}"))
