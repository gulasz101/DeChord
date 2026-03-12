from dataclasses import dataclass
from pathlib import Path


def default_runtime_root() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class RuntimePaths:
    root: Path

    @property
    def uploads_dir(self) -> Path:
        return self.root / "uploads"

    @property
    def stems_dir(self) -> Path:
        return self.root / "stems"

    @property
    def cache_dir(self) -> Path:
        return self.root / "cache"

    def ensure_dirs(self) -> None:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.stems_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


runtime_paths = RuntimePaths(root=default_runtime_root())
