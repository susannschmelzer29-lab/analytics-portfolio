import pytest

from pflege_rag.chunking import SourceFormatError, chunk_document, parse_front_matter
from pflege_rag.generate import _sentences

DOC = """---
titel: Test
paragraf: § 1 SGB XI
quelle: Testquelle
url: https://example.org
stand: 2026-01-01
---

Preamble is ignored.

## Erster Abschnitt

Text eins nach § 37 Abs. 3 SGB XI. Zweiter Satz.

## Leer

## Liste

Die Beträge:

- Pflegegrad 2: 347 Euro
- Pflegegrad 3: 599 Euro
"""


def test_one_chunk_per_section_and_empty_sections_skipped():
    chunks = chunk_document(DOC, "t")
    assert [c.heading for c in chunks] == ["Erster Abschnitt", "Liste"]
    assert [c.chunk_id for c in chunks] == ["t#1", "t#2"]


def test_chunk_text_carries_title_and_paragraph():
    c = chunk_document(DOC, "t")[0]
    assert c.text.startswith("Test (§ 1 SGB XI): Erster Abschnitt")
    assert c.citation.startswith("§ 1 SGB XI – Erster Abschnitt")


@pytest.mark.parametrize(
    "bad",
    ["no front matter", "---\ntitel: x\n---\n## a\nb", "---\ntitel x\n---\n## a\nb"],
)
def test_bad_front_matter_is_rejected(bad):
    with pytest.raises(SourceFormatError):
        parse_front_matter(bad) if "##" not in bad else chunk_document(bad, "x")


def test_document_without_sections_is_rejected():
    head = DOC.split("Preamble")[0]
    with pytest.raises(SourceFormatError):
        chunk_document(head + "only text", "x")


def test_abbreviations_do_not_split_sentences():
    sents = _sentences(chunk_document(DOC, "t")[0])
    assert sents == ["Text eins nach § 37 Abs. 3 SGB XI.", "Zweiter Satz."]


def test_list_items_inherit_their_intro():
    sents = _sentences(chunk_document(DOC, "t")[1])
    assert sents == ["Die Beträge: Pflegegrad 2: 347 Euro", "Die Beträge: Pflegegrad 3: 599 Euro"]
