import numpy as np
import pytest

from pflege_rag.chunking import Chunk
from pflege_rag.embeddings import HashingEmbedder, make_embedder
from pflege_rag.store import EmbedderMismatch, MemoryStore


def test_hashing_is_deterministic_and_normalised():
    e = HashingEmbedder()
    a = e.embed(["Pflegegeld bei Pflegegrad 3", "Pflegegeld bei Pflegegrad 3"])
    assert np.allclose(a[0], a[1])
    assert np.allclose(np.linalg.norm(a, axis=1), 1.0)


def test_inflected_compounds_stay_close():
    e = HashingEmbedder()
    q, near, far = e.embed(["Höhe des Pflegegeldes", "Pflegegeld beträgt 599 Euro", "Wetter in Schwerin"])
    assert q @ near > q @ far


def test_empty_text_gives_zero_vector_not_nan():
    v = HashingEmbedder().embed([""])
    assert not np.isnan(v).any()


def test_unknown_embedder_is_rejected():
    with pytest.raises(ValueError):
        make_embedder("word2vec")


def _chunks(n):
    return [Chunk(f"c#{i}", f"h{i}", f"text {i}", {"source_file": "c"}) for i in range(n)]


def test_memory_store_ranks_by_cosine():
    store = MemoryStore()
    store.add(_chunks(3), np.eye(3, dtype=np.float32))
    hits = store.query(np.array([0, 1, 0], dtype=np.float32), k=2)
    assert hits[0][0].chunk_id == "c#1" and hits[0][1] == pytest.approx(1.0)
    assert len(hits) == 2


def test_memory_store_rejects_length_mismatch():
    with pytest.raises(ValueError):
        MemoryStore().add(_chunks(2), np.eye(3, dtype=np.float32))


def test_chroma_roundtrip_and_embedder_guard(tmp_path):
    pytest.importorskip("chromadb")
    from pflege_rag.store import ChromaStore

    vecs = np.eye(3, dtype=np.float32)
    store = ChromaStore(tmp_path, "hashing-4096", reset=True)
    store.add(_chunks(3), vecs)
    hits = ChromaStore(tmp_path, "hashing-4096").query(vecs[2], k=1)
    assert hits[0][0].chunk_id == "c#2"
    assert hits[0][0].meta == {"source_file": "c"}
    assert hits[0][1] == pytest.approx(1.0, abs=1e-4)
    with pytest.raises(EmbedderMismatch):
        ChromaStore(tmp_path, "another-model")
