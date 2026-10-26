import json

import pytest

from pflege_rag import SOURCE_DIR
from pflege_rag.embeddings import HashingEmbedder
from pflege_rag.evaluation import canonical_numbers, contains, g_cites_sources, g_no_invented_numbers, run
from pflege_rag.generate import BrokenGenerator, ExtractiveGenerator
from pflege_rag.pipeline import Answer, build_memory_pipeline


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1.497 Euro", {"1497"}),
        ("239,60 Euro", {"239.6"}),
        ("ab 12,5 bis unter 27", {"12.5", "27"}),
        ("4.180 Euro [2]", {"4180"}),
        ("100 Prozent", {"100"}),
    ],
)
def test_canonical_numbers(text, expected):
    assert canonical_numbers(text) == expected


def test_contains_numbers_and_text():
    assert contains("bis zu 2.299 Euro", "2.299")
    assert not contains("bis zu 2.299 Euro", "229")
    assert contains("Die Pflicht ist ENTFALLEN", "entfallen")


def _answer(text, context="Pflegegrad 3: 599 Euro"):
    from pflege_rag.chunking import Chunk

    return Answer("q", text, refused=False, retrieved=[(Chunk("x#1", "h", context, {}), 0.9)])


def test_invented_number_is_blocking():
    c = g_no_invented_numbers({}, _answer("Es gibt 600 Euro [1]."))
    assert c.severity == "blocking" and not c.passed and "600" in c.detail


def test_citation_must_point_to_a_retrieved_passage():
    assert g_cites_sources({}, _answer("599 Euro [1]")).passed
    assert not g_cites_sources({}, _answer("599 Euro [2]")).passed
    assert not g_cites_sources({}, _answer("599 Euro")).passed


def test_offline_evaluation_passes(root, tmp_path):
    p = build_memory_pipeline(SOURCE_DIR, HashingEmbedder(), ExtractiveGenerator())
    report = run(p, root / "cases" / "questions.json")
    assert not report.blocking, report.blocking
    assert report.exit_code == 0, report.failed_gates


def test_broken_generator_is_blocked(root):
    p = build_memory_pipeline(SOURCE_DIR, HashingEmbedder(), BrokenGenerator())
    report = run(p, root / "cases" / "questions.json")
    graders = {c.grader for _, c in report.blocking}
    assert {"no_invented_numbers", "cites_sources"} <= graders
    assert report.exit_code == 1


def test_disabling_the_refusal_threshold_is_caught(root):
    # Without the threshold the system answers the weather question from
    # unrelated passages. The evaluation must notice.
    p = build_memory_pipeline(SOURCE_DIR, HashingEmbedder(), ExtractiveGenerator(), min_similarity=0.0, use_guard=False)
    report = run(p, root / "cases" / "questions.json")
    assert any(c.grader == "refuses_out_of_scope" for _, c in report.blocking)


def test_cases_file_is_well_formed(root):
    data = json.loads((root / "cases" / "questions.json").read_text(encoding="utf-8"))
    cats = {c["category"] for c in data["cases"]}
    assert {"amount", "rule", "out_of_scope", "injection"} <= cats
    for c in data["cases"]:
        if c.get("expect_source"):
            assert (SOURCE_DIR / f"{c['expect_source']}.md").exists(), c["id"]
