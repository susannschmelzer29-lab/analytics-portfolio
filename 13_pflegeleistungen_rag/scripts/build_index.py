"""Build the ChromaDB index from data/sources/*.md.

    python scripts/build_index.py                 # real multilingual model
    python scripts/build_index.py --embedder hashing   # offline, no download

Always rebuilds from scratch: the sources are small, and an index that has
been patched incrementally is an index nobody can reproduce.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pflege_rag import INDEX_DIR, SOURCE_DIR  # noqa: E402
from pflege_rag.chunking import load_chunks  # noqa: E402
from pflege_rag.embeddings import make_embedder  # noqa: E402
from pflege_rag.store import ChromaStore  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--embedder", default="st", choices=["st", "hashing"])
    p.add_argument("--index", type=Path, default=INDEX_DIR)
    args = p.parse_args(argv)

    t0 = time.perf_counter()
    chunks = load_chunks(SOURCE_DIR)
    print(f"{len(chunks)} chunks from {len({c.meta['source_file'] for c in chunks})} source files")

    embedder = make_embedder(args.embedder)
    print(f"embedding with {embedder.name} ...")
    vectors = embedder.embed([c.text for c in chunks])

    store = ChromaStore(args.index, embedder.name, reset=True)
    store.add(chunks, vectors)
    print(f"index written to {args.index} ({len(store)} vectors, {time.perf_counter() - t0:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
