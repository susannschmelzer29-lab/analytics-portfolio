import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pflege_rag import SOURCE_DIR  # noqa: E402
from pflege_rag.embeddings import HashingEmbedder  # noqa: E402
from pflege_rag.generate import ExtractiveGenerator  # noqa: E402
from pflege_rag.pipeline import build_memory_pipeline  # noqa: E402


@pytest.fixture(scope="session")
def pipeline():
    return build_memory_pipeline(SOURCE_DIR, HashingEmbedder(), ExtractiveGenerator())


@pytest.fixture(scope="session")
def root():
    return ROOT
