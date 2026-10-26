"""Streamlit front end.

    streamlit run app.py

Needs the index (python scripts/build_index.py). Uses Claude when
ANTHROPIC_API_KEY is set, otherwise the offline extractive generator - so
the app also works in an interview without a key or a network.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pflege_rag import INDEX_DIR  # noqa: E402
from pflege_rag.embeddings import make_embedder  # noqa: E402
from pflege_rag.generate import make_generator  # noqa: E402
from pflege_rag import SOURCE_DIR  # noqa: E402
from pflege_rag.chunking import load_chunks  # noqa: E402
from pflege_rag.pipeline import DISCLAIMER, LexicalGuard, RagPipeline  # noqa: E402
from pflege_rag.scoring import ANLAGE_2, calculate  # noqa: E402
from pflege_rag.store import ChromaStore  # noqa: E402

st.set_page_config(page_title="Pflegeleistungen-Assistent", page_icon="🩺", layout="centered")

EXAMPLES = [
    "Wie hoch ist das Pflegegeld bei Pflegegrad 3?",
    "Ab wie vielen Punkten gilt Pflegegrad 4?",
    "Wie viel Geld gibt es für Verhinderungspflege und Kurzzeitpflege im Jahr?",
    "Was bekomme ich bei Pflegegrad 1?",
]


@st.cache_resource
def load_pipeline(embedder_kind: str, generator_kind: str) -> RagPipeline:
    embedder = make_embedder(embedder_kind)
    store = ChromaStore(INDEX_DIR, embedder.name)
    if len(store) == 0:
        raise RuntimeError("Index is empty. Run: python scripts/build_index.py")
    guard = LexicalGuard(load_chunks(SOURCE_DIR))
    return RagPipeline(embedder, store, make_generator(generator_kind), guard=guard)


st.title("Pflegeleistungen 2026")
st.caption("Fragen zu Pflegegraden und Leistungen der Pflegeversicherung (SGB XI) – jede Antwort mit Quelle.")

with st.sidebar:
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    generator_kind = st.radio(
        "Antwort-Generator",
        ["claude", "extractive"],
        index=0 if has_key else 1,
        help="Ohne ANTHROPIC_API_KEY läuft nur der Offline-Generator.",
        disabled=not has_key,
    )
    embedder_kind = st.radio("Embeddings", ["st", "hashing"], help="Muss zum gebauten Index passen.")
    st.markdown("**Beispiele**")
    for ex in EXAMPLES:
        if st.button(ex, use_container_width=True):
            st.session_state["q"] = ex

MODULE_NAMES = {
    1: "Mobilität",
    2: "Kognitive und kommunikative Fähigkeiten",
    3: "Verhaltensweisen und psychische Problemlagen",
    4: "Selbstversorgung",
    5: "Krankheits- und therapiebedingte Anforderungen",
    6: "Alltagsleben und soziale Kontakte",
}

tab_ask, tab_calc = st.tabs(["Fragen", "Pflegegrad-Rechner"])

with tab_calc:
    st.caption(
        "Gewichtete Punkte nach Anlage 2 zu § 15 SGB XI, für Erwachsene. "
        "Gerechnet wird in Python, nicht vom Sprachmodell."
    )
    points = {
        m: st.number_input(f"Modul {m}: {name} (Einzelpunkte)", 0, ANLAGE_2[m][-1][1], 0, key=f"m{m}")
        for m, name in MODULE_NAMES.items()
    }
    result = calculate({m: int(v) for m, v in points.items()})
    st.metric("Ergebnis", f"Pflegegrad {result.pflegegrad}" if result.pflegegrad else "kein Pflegegrad")
    st.markdown(result.explain())
    st.caption("Nur Rechenhilfe. Den Pflegegrad stellt die Pflegekasse nach der Begutachtung fest.")

with tab_ask:
    question = st.text_input("Ihre Frage", key="q")

    if question:
        try:
            pipe = load_pipeline(embedder_kind, generator_kind)
        except Exception as exc:  # show setup problems in the UI, not as a stack trace
            st.error(str(exc))
            st.stop()

        answer = pipe.ask(question)
        if answer.refused:
            st.warning(answer.text)
        else:
            st.markdown(answer.text)
            st.markdown("**Quellen**")
            for i, (chunk, score) in enumerate(answer.retrieved, 1):
                if chunk in answer.cited:
                    st.markdown(f"[{i}] {chunk.citation} – [Link]({chunk.meta.get('url')})")
        with st.expander("Abgerufene Passagen (Retrieval)"):
            for i, (chunk, score) in enumerate(answer.retrieved, 1):
                st.markdown(f"**[{i}] {chunk.chunk_id}** · Ähnlichkeit {score:.2f}")
                st.text(chunk.text)
        st.caption(DISCLAIMER)
