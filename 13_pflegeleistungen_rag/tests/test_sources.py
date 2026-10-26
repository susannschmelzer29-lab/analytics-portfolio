"""The knowledge base itself is tested like data, not trusted like prose.

Figures that appear in several files must agree, and figures that follow
from others must be derivable. A typo in one Pflegegeld amount would
otherwise surface only as a confidently wrong answer.
"""

import re
from decimal import Decimal

import pytest

from pflege_rag import SOURCE_DIR
from pflege_rag.chunking import REQUIRED_META, load_chunks, parse_front_matter

FILES = sorted(SOURCE_DIR.glob("*.md"))
TEXT = {f.stem: f.read_text(encoding="utf-8") for f in FILES}
ALL = "\n".join(TEXT.values())

PFLEGEGELD = {2: "347", 3: "599", 4: "800", 5: "990"}


def euro(s: str) -> Decimal:
    return Decimal(s.replace(".", "").replace(",", "."))


def test_fifteen_source_files():
    assert len(FILES) == 15


@pytest.mark.parametrize("f", FILES, ids=lambda f: f.stem)
def test_every_source_declares_its_origin(f):
    meta, _ = parse_front_matter(f.read_text(encoding="utf-8"), f.stem)
    for key in REQUIRED_META:
        assert meta[key], key
    assert meta["url"].startswith("https://")
    assert meta["stand"].startswith("2026")


def test_chunk_ids_unique():
    ids = [c.chunk_id for c in load_chunks(SOURCE_DIR)]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("grad,amount", PFLEGEGELD.items())
def test_pflegegeld_table(grad, amount):
    assert f"Pflegegrad {grad}: {amount} Euro im Monat" in TEXT["05_pflegegeld"]


@pytest.mark.parametrize("grad,amount", PFLEGEGELD.items())
def test_verhinderungspflege_relatives_is_twice_pflegegeld(grad, amount):
    m = re.search(rf"Pflegegrad {grad} bis zu ([\d.]+) Euro", TEXT["07_verhinderungs_kurzzeitpflege"])
    assert m, f"no Verhinderungspflege amount for Pflegegrad {grad}"
    assert euro(m.group(1)) == 2 * euro(amount)


def test_combination_example_is_arithmetically_correct():
    text = TEXT["06_kombinationsleistung"]
    assert "1.497" in text and "599" in text  # matches 04 and 05
    assert Decimal("599") * Decimal("0.40") == euro("239,60")
    assert "239,60 Euro" in text


@pytest.mark.parametrize(
    "figure,expected_files",
    [
        ("131 Euro", ["03_pflegegrad_1", "07_verhinderungs_kurzzeitpflege", "10_vollstationaere_pflege", "11_entlastungsbetrag"]),
        ("3.539 Euro", ["07_verhinderungs_kurzzeitpflege"]),
        ("1.497 Euro", ["04_pflegesachleistung", "06_kombinationsleistung"]),
    ],
)
def test_shared_figures_are_consistent(figure, expected_files):
    for stem in expected_files:
        assert figure in TEXT[stem], f"{figure} missing in {stem}"


def test_no_stale_2024_amounts():
    # Pflegegeld/Sachleistung before 1.1.2025. Must never reappear.
    for stale in ("332 Euro", "573 Euro", "765 Euro", "947 Euro", "761 Euro", "4.000 Euro", "125 Euro"):
        assert stale not in ALL, stale


def test_pflegegrad_thresholds_are_ordered():
    pts = [euro(x) for x in re.findall(r"Pflegegrad \d: ab ([\d,]+) bis", TEXT["02_pflegegrade"])]
    assert pts == sorted(pts) and pts[0] == Decimal("12.5")
