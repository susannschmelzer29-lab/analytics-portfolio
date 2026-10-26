"""Question in, cited answer (or an honest refusal) out.

Three checks can refuse, on purpose:

1. **Lexical guard** - the question must share wording with the sources.
   Semantic models rate "Bürgergeld" close to "Pflegegeld" (both are money
   from the state); character n-grams do not. The two signals fail in
   different ways, so the guard runs whichever embedder does the retrieval.
2. **Semantic threshold** - if even the best passage is only weakly similar,
   the generator is never called. No context, no answer.
3. **In generation** - the generator answers ``NOT_FOUND`` when the passages
   do not contain the answer.

Either way the user gets the same fixed refusal text. A wrong amount in a
care context costs someone money; "Das steht nicht in meinen Quellen" costs
them a phone call to the Pflegekasse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .chunking import Chunk, load_chunks
from .embeddings import Embedder, HashingEmbedder
from .generate import NOT_FOUND, Generator
from .store import MemoryStore, VectorStore

REFUSAL = (
    "Dazu enthalten meine Quellen keine Angabe. Bitte wenden Sie sich an Ihre "
    "Pflegekasse oder einen Pflegestützpunkt."
)
DISCLAIMER = "Allgemeine Information, keine Rechtsberatung im Einzelfall."

# Calibrated per embedder from the evaluation (cases/questions.json) - see
# README, decision 2. With the multilingual model, out-of-scope questions
# reached 0.59 while in-scope ones went down to 0.52: no semantic threshold
# separates them, which is why the lexical guard exists.
MIN_SIMILARITY = {
    "hashing": 0.25,
    "sentence-transformers": 0.30,
}
# Lexical overlap (HashingEmbedder cosine): in-scope >= 0.32, out-of-scope <= 0.20.
MIN_LEXICAL = 0.25

_CITE = re.compile(r"\[(\d+)\]")


@dataclass
class Answer:
    question: str
    text: str
    refused: bool
    retrieved: list[tuple[Chunk, float]] = field(default_factory=list)
    cited: list[Chunk] = field(default_factory=list)
    raw: str = ""
    lexical: float | None = None  # lexical-guard score, if a guard ran

    @property
    def context_text(self) -> str:
        return "\n".join(c.text for c, _ in self.retrieved)


def threshold_for(embedder: Embedder) -> float:
    key = "hashing" if embedder.name.startswith("hashing") else "sentence-transformers"
    return MIN_SIMILARITY[key]


class LexicalGuard:
    """Best character-n-gram similarity between the question and any chunk."""

    def __init__(self, chunks: list[Chunk], min_similarity: float = MIN_LEXICAL):
        self._embedder = HashingEmbedder()
        self._store = MemoryStore()
        self._store.add(chunks, self._embedder.embed([c.text for c in chunks]))
        self.min_similarity = min_similarity

    def score(self, question: str) -> float:
        hits = self._store.query(self._embedder.embed([question])[0], 1)
        return hits[0][1] if hits else 0.0

    def allows(self, question: str) -> bool:
        return self.score(question) >= self.min_similarity


class RagPipeline:
    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        generator: Generator,
        k: int = 4,
        min_similarity: float | None = None,
        guard: LexicalGuard | None = None,
    ):
        self.embedder = embedder
        self.store = store
        self.generator = generator
        self.k = k
        self.min_similarity = threshold_for(embedder) if min_similarity is None else min_similarity
        self.guard = guard

    def retrieve(self, question: str) -> list[tuple[Chunk, float]]:
        vec = self.embedder.embed([question])[0]
        return self.store.query(vec, self.k)

    def ask(self, question: str) -> Answer:
        question = question.strip()
        hits = self.retrieve(question) if question else []
        lexical = self.guard.score(question) if (self.guard is not None and question) else None
        if lexical is not None and lexical < self.guard.min_similarity:
            return Answer(question, REFUSAL, refused=True, retrieved=hits, lexical=lexical)
        if not hits or hits[0][1] < self.min_similarity:
            return Answer(question, REFUSAL, refused=True, retrieved=hits, lexical=lexical)

        chunks = [c for c, _ in hits]
        raw = self.generator.generate(question, chunks)
        if NOT_FOUND in raw:
            return Answer(question, REFUSAL, refused=True, retrieved=hits, raw=raw, lexical=lexical)

        cited_idx = sorted({int(n) for n in _CITE.findall(raw)})
        cited = [chunks[i - 1] for i in cited_idx if 1 <= i <= len(chunks)]
        return Answer(question, raw, refused=False, retrieved=hits, cited=cited, raw=raw, lexical=lexical)


def build_memory_pipeline(
    source_dir: Path, embedder: Embedder, generator: Generator, use_guard: bool = True, **kw
) -> RagPipeline:
    """Index the sources in memory. Used by tests and the evaluation."""
    chunks = load_chunks(source_dir)
    store = MemoryStore()
    store.add(chunks, embedder.embed([c.text for c in chunks]))
    guard = LexicalGuard(chunks) if use_guard else None
    return RagPipeline(embedder, store, generator, guard=guard, **kw)
