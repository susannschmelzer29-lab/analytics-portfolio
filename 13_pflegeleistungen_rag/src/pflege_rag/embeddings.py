"""Two interchangeable embedders behind one small interface.

* ``SentenceTransformerEmbedder`` - the real one. A multilingual model that
  runs locally on CPU: no API key, no per-call cost, and no care-related
  question ever leaves the machine. That last point is the reason for the
  choice, not a side effect - in a care context the question itself can be
  health data.
* ``HashingEmbedder`` - deterministic character n-gram hashing. No download,
  no network, same vector on every machine. It exists so the test suite and
  the CI evaluation run offline, and so the evaluation can show how much the
  real model actually adds (see README, "Baseline vs. model").
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Protocol, Sequence

import numpy as np

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class Embedder(Protocol):
    name: str

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Return an (n, d) float32 array of L2-normalised vectors."""
        ...


def _normalise(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (m / norms).astype(np.float32)


_WORD = re.compile(r"[a-zäöüß0-9]+(?:[.,][0-9]+)?", re.IGNORECASE)


class HashingEmbedder:
    """Bag of character n-grams, hashed into a fixed number of buckets.

    Character n-grams matter for German: "Pflegegeldes", "Pflegegeld" and
    "Pflegegeldbezieher" share most of their trigrams, so compound words and
    inflections still meet without a stemmer.
    """

    def __init__(self, dim: int = 4096, ngram: tuple[int, int] = (3, 5)):
        self.dim = dim
        self.ngram = ngram
        self.name = f"hashing-{dim}"

    def _bucket(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "little") % self.dim

    def _features(self, text: str) -> Counter:
        feats: Counter = Counter()
        for word in _WORD.findall(text.lower()):
            feats["w:" + word] += 2  # whole words weigh more than fragments
            padded = f" {word} "
            lo, hi = self.ngram
            for n in range(lo, hi + 1):
                for i in range(len(padded) - n + 1):
                    feats["c:" + padded[i : i + n]] += 1
        return feats

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        m = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for feat, count in self._features(text).items():
                m[row, self._bucket(feat)] += 1.0 + math.log(count)
        return _normalise(m)


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - exercised manually
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Run `pip install -r requirements.txt`, or use --embedder hashing."
            ) from exc
        self._model = SentenceTransformer(model_name)
        self.name = model_name

    def embed(self, texts: Sequence[str]) -> np.ndarray:  # pragma: no cover
        vecs = self._model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32)


def make_embedder(kind: str) -> Embedder:
    if kind == "hashing":
        return HashingEmbedder()
    if kind in ("st", "sentence-transformers", "model"):
        return SentenceTransformerEmbedder()
    raise ValueError(f"unknown embedder {kind!r} (use 'st' or 'hashing')")
