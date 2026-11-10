"""The owner's application folder: read, never written.

Same idea as data/raw/ in project 10. The class offers listing and reading and
nothing else. A write mode is refused, and so is any path outside the folder.

The pipeline's own folder may sit inside the application folder (it holds the
private config and the outputs). It is skipped when the folder is read, so the
pipeline never mistakes its own files for application documents.
"""

from __future__ import annotations

from pathlib import Path

WRITE_FLAGS = set("wax+")


class ApplicationFolder:
    def __init__(self, root: str | Path, skip: str | None = None):
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise FileNotFoundError(f"application folder not found: {self.root}")
        self.skip = (self.root / skip).resolve() if skip else None

    def _skipped(self, path: Path) -> bool:
        return self.skip is not None and (path == self.skip or self.skip in path.parents)

    def _inside(self, relative: str | Path) -> Path:
        path = (self.root / relative).resolve()
        if path != self.root and self.root not in path.parents:
            raise PermissionError(f"outside the application folder: {relative}")
        return path

    def open(self, relative: str | Path, mode: str = "rb"):
        if WRITE_FLAGS & set(mode):
            raise PermissionError("the application folder is read-only")
        return open(self._inside(relative), mode)

    def files(self, pattern: str = "*") -> list[Path]:
        return sorted(
            p.relative_to(self.root)
            for p in self.root.rglob(pattern)
            if p.is_file() and not self._skipped(p.resolve())
        )

    def subfolders(self, relative: str | Path = ".") -> list[str]:
        base = self._inside(relative)
        return sorted(p.name for p in base.iterdir() if p.is_dir() and not self._skipped(p.resolve()))
