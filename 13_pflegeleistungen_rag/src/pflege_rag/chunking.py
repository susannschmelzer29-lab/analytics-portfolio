"""Turn the Markdown knowledge base into retrievable chunks.

One chunk = one ``##`` section. Sections in the sources are written to be
self-contained (each names its paragraph and its subject), so a heading
boundary is also a meaning boundary. That is the main reason this project
does not use fixed-size token windows: a window that cuts the Pflegegeld
table in half retrieves half a table.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_META = ("titel", "paragraf", "quelle", "url", "stand")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str  # "05_pflegegeld#2" - file stem + section index
    heading: str
    text: str  # heading + body, what gets embedded and shown
    meta: dict = field(default_factory=dict, hash=False, compare=False)

    @property
    def paragraf(self) -> str:
        return self.meta.get("paragraf", "")

    @property
    def citation(self) -> str:
        """Human-readable source line, shown under every answer."""
        return f"{self.meta.get('paragraf', '?')} – {self.heading} ({self.meta.get('quelle', '?')})"


class SourceFormatError(ValueError):
    pass


def parse_front_matter(raw: str, name: str = "<source>") -> tuple[dict, str]:
    if not raw.startswith("---"):
        raise SourceFormatError(f"{name}: missing front matter")
    try:
        _, head, body = raw.split("---", 2)
    except ValueError as exc:
        raise SourceFormatError(f"{name}: unterminated front matter") from exc
    meta = {}
    for line in head.strip().splitlines():
        key, sep, value = line.partition(":")
        if not sep:
            raise SourceFormatError(f"{name}: bad front-matter line {line!r}")
        meta[key.strip()] = value.strip()
    missing = [k for k in REQUIRED_META if not meta.get(k)]
    if missing:
        raise SourceFormatError(f"{name}: missing {', '.join(missing)}")
    return meta, body


def chunk_document(raw: str, stem: str) -> list[Chunk]:
    meta, body = parse_front_matter(raw, stem)
    meta = {**meta, "source_file": stem}
    parts = re.split(r"^## +(.+)$", body, flags=re.MULTILINE)
    # parts = [preamble, heading1, body1, heading2, body2, ...]
    chunks = []
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        text = parts[i + 1].strip()
        if not text:
            continue
        idx = len(chunks) + 1
        chunks.append(
            Chunk(
                chunk_id=f"{stem}#{idx}",
                heading=heading,
                text=f"{meta['titel']} ({meta['paragraf']}): {heading}\n\n{text}",
                meta=meta,
            )
        )
    if not chunks:
        raise SourceFormatError(f"{stem}: no '## ' sections found")
    return chunks


def load_chunks(source_dir: Path) -> list[Chunk]:
    files = sorted(Path(source_dir).glob("*.md"))
    if not files:
        raise FileNotFoundError(f"no .md sources in {source_dir}")
    out: list[Chunk] = []
    for f in files:
        out.extend(chunk_document(f.read_text(encoding="utf-8"), f.stem))
    return out
