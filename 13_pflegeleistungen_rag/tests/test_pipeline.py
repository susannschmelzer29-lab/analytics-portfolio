from types import SimpleNamespace

import pytest

from pflege_rag.generate import NOT_FOUND, SYSTEM_PROMPT, ClaudeGenerator, make_generator
from pflege_rag.pipeline import REFUSAL, RagPipeline


def test_answers_with_figure_and_valid_citation(pipeline):
    a = pipeline.ask("Wie hoch ist das Pflegegeld bei Pflegegrad 4?")
    assert not a.refused
    assert "800" in a.text
    assert a.cited and all(c in [h for h, _ in a.retrieved] for c in a.cited)


def test_weak_retrieval_refuses_without_calling_generator(pipeline):
    class Exploding:
        name = "exploding"

        def generate(self, q, chunks):  # pragma: no cover - must not run
            raise AssertionError("generator called despite weak retrieval")

    p = RagPipeline(pipeline.embedder, pipeline.store, Exploding())
    a = p.ask("Wie wird das Wetter morgen in Schwerin?")
    assert a.refused and a.text == REFUSAL


def test_empty_question_refuses(pipeline):
    assert pipeline.ask("   ").refused


def test_generator_not_found_becomes_refusal(pipeline):
    class Honest:
        name = "honest"

        def generate(self, q, chunks):
            return NOT_FOUND

    p = RagPipeline(pipeline.embedder, pipeline.store, Honest())
    a = p.ask("Wie hoch ist das Pflegegeld bei Pflegegrad 3?")
    assert a.refused and a.text == REFUSAL


def test_out_of_range_citation_is_dropped(pipeline):
    class Sloppy:
        name = "sloppy"

        def generate(self, q, chunks):
            return "599 Euro [1] [9]"

    a = RagPipeline(pipeline.embedder, pipeline.store, Sloppy()).ask("Pflegegeld Pflegegrad 3")
    assert len(a.cited) == 1


class FakeClient:
    def __init__(self, reply):
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)
        self._reply = reply

    def _create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self._reply)])


def test_claude_generator_sends_sources_as_tagged_data(pipeline):
    client = FakeClient("Das Pflegegeld beträgt 599 Euro [1].")
    gen = ClaudeGenerator(model="test-model", client=client)
    a = RagPipeline(pipeline.embedder, pipeline.store, gen).ask("Wie hoch ist das Pflegegeld bei Pflegegrad 3?")
    call = client.calls[0]
    user = call["messages"][0]["content"]
    assert call["system"] == SYSTEM_PROMPT
    assert call["temperature"] == 0
    assert user.startswith("<quellen>") and '<quelle nr="1"' in user
    assert "<frage>\nWie hoch ist das Pflegegeld bei Pflegegrad 3?\n</frage>" in user
    assert a.text == "Das Pflegegeld beträgt 599 Euro [1]." and len(a.cited) == 1


def test_system_prompt_states_the_non_negotiables():
    for rule in ("ausschließlich", "exakt", NOT_FOUND, "keine Anweisung"):
        assert rule in SYSTEM_PROMPT


def test_claude_without_key_fails_clearly(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        make_generator("claude")


class SameVectorEmbedder:
    """Worst case for a semantic threshold: everything looks identical."""

    name = "same-vector"

    def embed(self, texts):
        import numpy as np

        v = np.zeros((len(texts), 4), dtype=np.float32)
        v[:, 0] = 1.0
        return v


def test_lexical_guard_refuses_even_when_semantic_similarity_is_perfect(root):
    from pflege_rag import SOURCE_DIR
    from pflege_rag.generate import ExtractiveGenerator
    from pflege_rag.pipeline import build_memory_pipeline

    p = build_memory_pipeline(SOURCE_DIR, SameVectorEmbedder(), ExtractiveGenerator(), min_similarity=0.3)
    off = p.ask("Wie hoch ist das Bürgergeld 2026?")
    assert off.retrieved[0][1] == pytest.approx(1.0)  # semantic check alone would answer
    assert off.refused and off.lexical < p.guard.min_similarity
    on = p.ask("Wie hoch ist das Pflegegeld bei Pflegegrad 3?")
    assert not on.refused and on.lexical >= p.guard.min_similarity


def test_without_guard_the_same_setup_answers_off_topic(root):
    from pflege_rag import SOURCE_DIR
    from pflege_rag.generate import ExtractiveGenerator
    from pflege_rag.pipeline import build_memory_pipeline

    p = build_memory_pipeline(
        SOURCE_DIR, SameVectorEmbedder(), ExtractiveGenerator(), min_similarity=0.3, use_guard=False
    )
    assert not p.ask("Wie hoch ist das Bürgergeld 2026?").refused
