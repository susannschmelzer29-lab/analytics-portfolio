# Media Consumption Analysis — Content Strategy on a Data Foundation

> News content analysis for a marketing agency · **ABC News (AU)** & **HuffPost (US)**
> 1.45M headlines · 2 sources · 2003–2022 (20 years) · 6 key questions

A end-to-end analytics project: from two raw news datasets through a Python
processing pipeline to an interactive Tableau dashboard and a narrated
presentation. The goal — give a content-strategy team a data-backed view of which
topics matter, when, and how two very different newsrooms set their agenda.

---

## 🔗 Presentations

| | |
|---|---|
| **📊 Interactive dashboard** | [View on Tableau Public →](TABLEAU_VIEW_LINK_HERE) |
| **🎤 Narrated presentation** | [View on Prezi →](PREZI_VIEW_LINK_HERE) |

<!--
  Replace the two placeholders above AFTER publishing:
  - Tableau: publish to Tableau Public, then copy the public view URL
    (looks like https://public.tableau.com/views/...).
  - Prezi:  use the SHARE VIEW link (https://prezi.com/view/...),
    NOT the /p/edit/ link, and set visibility to public.
-->

---

## ❓ Key questions

1. **Distribution** — How do articles split across categories?
2. **Trend** — Which topics are most relevant over time?
3. **Seasonality** — Are there temporal patterns per category?
4. **Keywords** — Which terms dominate each category?
5. **Sources** — Which source/author focuses on which topic?
6. **Content length** — Do headline lengths differ by category?

---

## 🔑 Key findings

- **Two distinct editorial profiles.** ABC News is **hard-news-driven** (crime
  ~24 %, politics ~23 %); HuffPost leans **lifestyle** (entertainment ~24 %,
  health ~20 %). This contrast is the central result.
- **Politics rises at HuffPost from 2014** onward — visible once the sparse
  pre-2014 years are filtered out.
- **Headlines are uniformly short** (~7 words median across categories). The real
  length difference at HuffPost lives in the *description* text (service topics
  ~23–24 words vs. news ~14).
- **Clear author specialisation** at HuffPost — many authors concentrate close to
  100 % of their articles in a single category (beat reporting).

---

## 🛠️ Method

1. **Ingest & clean** two datasets (ABC headlines; HuffPost headlines +
   descriptions + native categories).
2. **Categorise ABC** via keyword matching on headline text (ABC has no native
   labels).
3. **Aggregate** by source / year / month / category to keep the dashboard fast
   (< 250 KB inputs instead of > 70 MB raw).
4. **Harmonise** all category labels to one canonical vocabulary
   (see `00_kategorie_mapping.csv`).
5. **Visualise** — six Tableau worksheets, one per question, combined into a
   single interactive dashboard.

> **Transparency note:** ABC categories are keyword-derived; ~60 % of ABC
> headlines remain **"Other"**, so ABC distribution figures describe the
> classified 40 %. The source comparison uses only the shared period and shared
> categories, normalised per source. Full detail in
> [`METHODOLOGY.md`](METHODOLOGY.md).

---

## 📁 Repository contents

| File | Purpose |
|---|---|
| `README.md` | This overview |
| `METHODOLOGY.md` | Canonical figures + methodological notes (DE & EN) |
| `Tableau_Bauanleitung.pdf` | Step-by-step guide to rebuild the dashboard |
| `data/00_kategorie_mapping.csv` | Documents the label harmonisation |
| `data/01_tableau_aggregiert.csv` | Counts & word lengths per source/year/month/category |
| `data/02_tableau_keywords.csv` | Top keywords per category & source |
| `data/03_tableau_autoren.csv` | Articles per author & category (HuffPost) |
| `data/04_tableau_vergleich.csv` | Topic share ABC vs. HuffPost (shared categories) |
| `data/kategorie_summary.csv` | ABC category distribution summary |
| `data/VS_quellenvergleich.csv` | Source comparison (long form) |

---

## 🧰 Tools

Python (pandas) · Tableau Public · Prezi

---

*Part of my [analytics portfolio](https://github.com/susannschmelzer29-lab/analytics-portfolio) — a résumé in projects.*
