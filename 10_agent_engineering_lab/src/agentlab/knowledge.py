"""Knowledge lookup over the project's own documentation.

What this replaces
-------------------
An earlier version reached into a separate retrieval project. That project
no longer exists, and the dependency was the wrong shape anyway: cloning
this repository gave you an ImportError instead of a working pipeline.

This version is self-contained. It retrieves from the Markdown files in
`docs/`, with no index, no embeddings and no network — a keyword score
over headed sections. For a handful of documents that is not a compromise;
it is the right amount of machinery, and it is explainable to a
stakeholder, which an embedding score is not.

SECURITY DECISION
-----------------
What comes back from a knowledge source is **data, not instruction.**
Retrieved passages go into the REPORT as quotations with a source. They
never enter a system prompt and never influence a tool decision.

A language model cannot reliably separate your instruction from a text it
has read — both are one token stream. Whoever can write into an indexed
document would otherwise steer the agent. That is the finding OWASP maps
onto six of the ten categories in its 2026 agentic top ten.

`_sanitise()` additionally strips lines that look like instructions. That
is a second layer, explicitly not a guarantee. The real boundary is
architectural: retrieval only ever reaches the report.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Protocol, runtime_checkable

from .models import Answer, Evidence


def _resolve_project_path(raw_path: str | Path) -> Path:
    """Resolve relative project data paths from either the current CWD or the package root."""
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate

    roots = [
        Path.cwd(),
        Path(__file__).resolve().parents[2],
        Path(__file__).resolve().parents[3],
    ]
    for root in roots:
        resolved = (root / candidate).resolve()
        if resolved.exists():
            return resolved
    return (Path(__file__).resolve().parents[2] / candidate).resolve()

MAX_EXCERPT = 400

_SUSPICIOUS = (
    "ignore previous", "ignore all", "disregard", "forget everything",
    "system:", "assistant:", "new instruction", "you are now",
)


def _sanitise(text: str) -> str:
    """Turns foreign text into a quotation."""
    lines = [ln for ln in text.splitlines()
             if not any(m in ln.lower() for m in _SUSPICIOUS)]
    return " ".join(" ".join(lines).split())[:MAX_EXCERPT]


@runtime_checkable
class KnowledgeSource(Protocol):
    """What a knowledge source must do — nothing more."""

    def ask(self, question: str, context: dict | None = None) -> Answer: ...

    @property
    def name(self) -> str: ...


class NoKnowledge:
    """The honest failure mode.

    Answers "unknown" rather than a plausible invention. A non-answer
    dressed as knowledge is worse than a gap.
    """

    name = "no source"

    def ask(self, question: str, context: dict | None = None) -> Answer:
        return Answer(
            question=question,
            text="unknown (no knowledge source configured)",
            evidence=(),
            grounded=False,
            source_name=self.name,
        )


class DocsKnowledge:
    """Keyword retrieval over the Markdown files in a directory.

    Sections are split on Markdown headings, because a heading is the
    author's own statement about where one topic ends — a better boundary
    than a fixed chunk size, and free.
    """

    name = "project docs"

    def __init__(self, docs_dir: str | Path = "docs") -> None:
        self.docs_dir = _resolve_project_path(docs_dir)
        self._sections: list[tuple[str, str]] | None = None
        self._idf_cache: dict[str, float] | None = None

    # -- availability ------------------------------------------------------

    @property
    def available(self) -> bool:
        return self.docs_dir.is_dir() and any(self.docs_dir.glob("*.md"))

    def diagnose(self) -> str:
        """Plain text on why the lookup does (not) work.

        A lookup that silently does nothing is the worst of all variants,
        which is why this is a method rather than a comment.
        """
        if not self.docs_dir.is_dir():
            return f"docs directory not found: {self.docs_dir}"
        files = list(self.docs_dir.glob("*.md"))
        if not files:
            return f"no .md files in {self.docs_dir}"
        return f"{len(files)} document(s), {len(self._load())} sections indexed"

    # -- retrieval ---------------------------------------------------------

    def _load(self) -> list[tuple[str, str]]:
        if self._sections is not None:
            return self._sections

        sections: list[tuple[str, str]] = []
        for path in sorted(self.docs_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            current_heading = path.name
            buffer: list[str] = []
            for line in text.splitlines():
                if line.startswith("#"):
                    if buffer:
                        sections.append((f"{path.name} › {current_heading}",
                                         "\n".join(buffer)))
                    current_heading = line.lstrip("#").strip()
                    buffer = []
                else:
                    buffer.append(line)
            if buffer:
                sections.append((f"{path.name} › {current_heading}", "\n".join(buffer)))

        self._sections = [(src, body) for src, body in sections if body.strip()]
        return self._sections

    # Function and question words. IDF is supposed to handle these, and on
    # a corpus of thousands of documents it would. On eleven sections it
    # cannot: "what" appears in three of them, which looks informative to
    # the statistics and is not. Combined with the heading weight below,
    # that produced a confident 0.66 for "What is the capital of Peru?"
    # against a section headed "What the rules never do".
    #
    # An explicit list is the honest fix for a small corpus, not a
    # workaround: it encodes knowledge the data is too small to supply.
    STOPWORDS = frozenset({
        "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
        "the", "and", "but", "for", "not", "are", "was", "were", "does", "did",
        "has", "have", "had", "can", "could", "should", "would", "will", "with",
        "from", "that", "this", "these", "those", "there", "then", "than",
        "its", "it's", "any", "all", "ever", "never", "also", "such", "into",
        "you", "your", "our", "their", "his", "her", "them", "they",
    })

    @classmethod
    def _tokens(cls, text: str) -> set[str]:
        # Three characters minimum: shorter tokens are almost all noise
        # ('of', 'in') and would flatten every score towards the same value.
        return {
            w for w in re.findall(r"[a-z0-9_]+", text.lower())
            if len(w) >= 3 and w not in cls.STOPWORDS
        }

    def _idf(self) -> dict[str, float]:
        """Inverse document frequency per term, computed once.

        Why plain overlap is not enough — and this is a bug this project
        actually had: 'What is the capital of Peru?' scored 0.5 against a
        section about repair rules, because 'what' and 'the' appear in
        almost every section. Two meaningless matches out of four terms
        looked like a hit.

        IDF fixes that without any machine learning: a term occurring in
        most sections carries almost no weight, a term occurring in one
        carries a lot. Still fully explainable to a stakeholder, which is
        the property an embedding score does not have.
        """
        if self._idf_cache is not None:
            return self._idf_cache

        sections = self._load()
        n = len(sections) or 1
        doc_freq: dict[str, int] = {}
        for src, body in sections:
            for term in self._tokens(body) | self._tokens(src):
                doc_freq[term] = doc_freq.get(term, 0) + 1

        # Clamped at zero, and this matters: log(n / (1 + df)) goes
        # NEGATIVE for a term appearing in nearly every section ("the",
        # "what"). A negative weight inverts the ratio and produced a
        # confident 0.659 for "What is the capital of Peru?" against a
        # section headed "What the rules never do".
        #
        # Clamped, a ubiquitous term contributes 0.01 -- present, but
        # unable to carry a match on its own.
        self._idf_cache = {
            term: max(math.log(n / (1 + df)), 0.0) + 0.01
            for term, df in doc_freq.items()
        }
        return self._idf_cache

    # A term matching the section HEADING is far stronger evidence than one
    # matching the body: a section headed "note" is what a question about
    # column 'note' is looking for, even when the body happens to use
    # different words for the same thing.
    #
    # This was not an optimisation but a repair. Without it, "Is column
    # 'note' mandatory?" retrieved nothing at all, because the documented
    # answer says "optional" and "free text" and never uses the words
    # "mandatory" or "value". Vocabulary mismatch is the standard failure
    # of keyword retrieval, and the heading is the cheapest way around it.
    HEADING_WEIGHT = 2.5

    def _score(self, question: str, body: str, source: str) -> float:
        """Share of the question's *informative* weight found in a section."""
        q = self._tokens(question)
        if not q:
            return 0.0

        idf = self._idf()
        # A term absent from every section is maximally informative, but it
        # cannot be matched — it still belongs in the denominator, otherwise
        # a question about something undocumented scores suspiciously well.
        unseen = math.log(max(len(self._load()), 1)) + 0.01
        weights = {t: idf.get(t, unseen) for t in q}
        total = sum(weights.values())
        if total <= 0:
            return 0.0

        in_body = self._tokens(body)
        in_heading = self._tokens(source)

        matched = 0.0
        for t, w in weights.items():
            if t in in_heading:
                matched += w * self.HEADING_WEIGHT
            elif t in in_body:
                matched += w

        # Capped: the heading boost may lift a section above the threshold,
        # it must not push a score past 1.0 and make "certainty" meaningless.
        return min(matched / total, 1.0)

    # -- protocol ----------------------------------------------------------

    def ask(self, question: str, context: dict | None = None) -> Answer:
        if not self.available:
            return Answer(question=question,
                          text=f"unknown ({self.diagnose()})",
                          grounded=False, source_name=self.name)

        scored = sorted(
            ((self._score(question, body, src), src, body)
             for src, body in self._load()),
            key=lambda t: t[0], reverse=True,
        )
        # Below a third of the question's terms, a hit is coincidence.
        # Returning it anyway would be the failure mode this whole module
        # is written to avoid.
        hits = [(s, src, body) for s, src, body in scored if s >= 0.34][:3]

        if not hits:
            return Answer(question=question,
                          text="unknown (nothing in the documentation matches)",
                          grounded=False, source_name=self.name)

        evidence = tuple(
            Evidence(source=src, excerpt=_sanitise(body), score=round(s, 3))
            for s, src, body in hits
        )
        return Answer(
            question=question,
            text=evidence[0].excerpt,
            evidence=evidence,
            # Grounded only when there is evidence. An answer without a
            # source is a claim, not knowledge.
            grounded=True,
            source_name=self.name,
        )


def question_for(code: str, file: str, column: str | None = None) -> str:
    """Builds the question for a finding code.

    A function rather than inline strings, so the questions live in one
    place and can be tested.
    """
    target = f"column '{column}'" if column else f"file '{file}'"
    questions = {
        "DUPLICATES": f"Which business key applies to {file}, and are duplicates ever permitted?",
        "TYPE_MISMATCH": f"Which data type is intended for {target}?",
        "MISSING_RED": f"Is {target} mandatory, and what does a missing value mean there?",
        "MISSING_AMBER": f"Is {target} mandatory, and what does a missing value mean there?",
        "CONSTANT": f"Is {target} expected to be constant, for example in a single-tenant export?",
        "KEY_MISSING": f"Which columns form the key of {file}?",
        "EMPTY": f"Is an empty delivery of {file} a known regular case?",
    }
    return questions.get(code, f"What does finding '{code}' mean for {target}?")
