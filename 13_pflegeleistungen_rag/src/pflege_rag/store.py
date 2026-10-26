"""Vector stores: ChromaDB on disk, plus an in-memory twin for tests.

Both return cosine similarity in [−1, 1] (higher = closer), so the refusal
threshold in ``pipeline.py`` means the same thing whichever store is used.

The Chroma collection records which embedder built it. Querying an index
with a different embedder than the one that built it does not crash - it
silently returns nonsense, because the vectors live in different spaces.
So the store refuses instead.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np

from .chunking import Chunk

COLLECTION = "pflegeleistungen"


class EmbedderMismatch(RuntimeError):
    pass


class VectorStore(Protocol):
    def add(self, chunks: Sequence[Chunk], vectors: np.ndarray) -> None: ...

    def query(self, vector: np.ndarray, k: int) -> list[tuple[Chunk, float]]: ...

    def __len__(self) -> int: ...


class MemoryStore:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._matrix = np.zeros((0, 0), dtype=np.float32)

    def add(self, chunks: Sequence[Chunk], vectors: np.ndarray) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors differ in length")
        self._chunks.extend(chunks)
        self._matrix = vectors if self._matrix.size == 0 else np.vstack([self._matrix, vectors])

    def query(self, vector: np.ndarray, k: int) -> list[tuple[Chunk, float]]:
        if not self._chunks:
            return []
        sims = self._matrix @ vector
        order = np.argsort(-sims, kind="stable")[:k]
        return [(self._chunks[i], float(sims[i])) for i in order]

    def __len__(self) -> int:
        return len(self._chunks)


class ChromaStore:
    """Persistent store. Rebuilt from scratch by ``scripts/build_index.py``."""

    def __init__(self, path: Path, embedder_name: str, reset: bool = False):
        import chromadb

        self._client = chromadb.PersistentClient(path=str(path))
        if reset:
            try:
                self._client.delete_collection(COLLECTION)
            except Exception:  # collection did not exist yet
                pass
        self._col = self._client.get_or_create_collection(
            COLLECTION,
            metadata={"hnsw:space": "cosine", "embedder": embedder_name},
        )
        built_with = (self._col.metadata or {}).get("embedder")
        if built_with and built_with != embedder_name:
            raise EmbedderMismatch(
                f"index at {path} was built with {built_with!r}, "
                f"but you are querying with {embedder_name!r}. "
                "Rebuild it: python scripts/build_index.py"
            )

    def add(self, chunks: Sequence[Chunk], vectors: np.ndarray) -> None:
        self._col.add(
            ids=[c.chunk_id for c in chunks],
            embeddings=[v.tolist() for v in vectors],
            documents=[c.text for c in chunks],
            metadatas=[{"heading": c.heading, "meta": json.dumps(c.meta, ensure_ascii=False)} for c in chunks],
        )

    def query(self, vector: np.ndarray, k: int) -> list[tuple[Chunk, float]]:
        res = self._col.query(query_embeddings=[vector.tolist()], n_results=k)
        out = []
        for cid, doc, md, dist in zip(
            res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            chunk = Chunk(chunk_id=cid, heading=md["heading"], text=doc, meta=json.loads(md["meta"]))
            out.append((chunk, 1.0 - float(dist)))  # cosine distance -> similarity
        return out

    def __len__(self) -> int:
        return self._col.count()
