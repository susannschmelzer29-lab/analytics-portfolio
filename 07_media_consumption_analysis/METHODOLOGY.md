# Media Consumption Analysis — Methodology & Key Figures

*News content analysis for a marketing agency · ABC News (AU) & HuffPost (US)*

This document fixes the canonical figures and the methodological caveats for the
project so that every artefact — slide deck, Tableau dashboard, and this
repository — tells one consistent story. All numbers below are verified directly
against the source data.

---

## 1. Canonical figures (use these everywhere)

| Figure | Value | Notes |
|---|---|---|
| Combined articles | **1,453,690** | ABC + HuffPost |
| ABC News (AU) articles | 1,244,182 | single source, headlines only |
| HuffPost (US) articles | 209,508 | headlines + short descriptions |
| Time span (combined) | **2003–2022 (20 calendar years)** | ABC 2003–2021, HuffPost 2012–2022 |
| Sources | 2 | ABC News, HuffPost |
| Leitfragen / key questions | 6 | distribution, trend, seasonality, keywords, sources, length |

> **Why the earlier "1.45 Mio. / 19 Jahre / 18 Jahre" numbers drifted:**
> 1.45 M is correct — it refers to *both* sources combined. The year span,
> however, was previously misstated. The true combined span is 2003–2022, i.e.
> **20 calendar years** (ABC begins Feb 2003, HuffPost ends 2022). Use 20, not
> 18 or 19.

---

## 2. Methodological caveats (state these openly)

These are honest limitations of the data, not errors in the analysis. Naming them
up front strengthens the credibility of the conclusions.

**a) ABC categorisation: 60 % "Other".**
ABC News provides only headlines, with no native category labels. Categories were
assigned by keyword matching on the headline text. This rule cleanly classifies
~40 % of articles; the remaining **60.0 % fall into "Other" (Sonstiges)**.
Consequence: every ABC distribution statement describes the *classified* 40 %, not
the full corpus. The pattern (crime- and politics-heavy) is robust, but absolute
shares should be read as "share of classified articles".

**b) HuffPost vs. ABC are not perfectly comparable.**
HuffPost carries editor-assigned categories and short description texts; ABC has
neither. The source comparison (Sheet 5b / file `04_tableau_vergleich.csv`) is
therefore restricted to the overlapping period and to the eight categories that
exist in both, normalised to 100 % per source.

**c) HuffPost politics coverage starts in 2014.**
The "Politics" category is sparsely populated before 2014, so the rising
political-coverage trend should be read from **2014 onward**. Filtering earlier
years out of the trend chart avoids a misleading near-zero baseline.

**d) Pre-aggregation.**
The Tableau inputs are deliberately pre-aggregated (< 250 KB total instead of
> 70 MB raw) by source / year / month / category. This keeps the public dashboard
fast and is the reason absolute counts, not raw rows, appear in Tableau.

---
### 2a. ABC News Categorization — Keyword-Based (Updated)

ABC News does not provide native categories. Each headline is assigned to
one of 8 content categories via keyword matching; anything that cannot be
matched unambiguously falls into `Sonstiges` (Other).

**Current value: 67.7% `Sonstiges`.**

Version history note: An earlier version of this document listed 60.0%
here. The original keyword rules that produced that value are no longer
available (code loss). The current pipeline uses a reconstructed,
documented keyword list (see `01_media_pipeline_1.ipynb`, section 3a) and
reproducibly yields a different value. An "Other" share of this magnitude
is plausible for pure headline-based keyword classification without full
text or context, and is treated as a methodological limitation, not a
data quality problem: short news headlines (avg. 7 words) often provide
too little context for unambiguous keyword matches.

## 3. Slide text — German (für das Deck)

### Titelfolie
> **Medienkonsum-Analyse**
> Content-Strategie auf Datenbasis
>
> 1,45 Mio. Schlagzeilen · 2 Quellen (ABC News & HuffPost) · 2003–2022 (20 Jahre) · 6 Leitfragen

### Fazit-Folie — methodische Hinweise
> **Transparente Hinweise zur Methodik**
> - ABC liefert nur Schlagzeilen; Kategorien wurden per Keyword-Zuordnung
>   gebildet. **60 % bleiben „Sonstiges"** — ABC-Verteilungsaussagen beziehen sich
>   auf die klassifizierten 40 %.
> - Quellenvergleich nur auf gemeinsamem Zeitraum und gemeinsamen Kategorien,
>   je Quelle auf 100 % normiert.
> - HuffPost-Politik erst ab 2014 belastbar erfasst — Trend ab 2014 lesen.
> - Daten bewusst vor-aggregiert für ein schnelles, interaktives Dashboard.
>
> *Trotz dieser Grenzen sind die Kernmuster stabil: ABC = Hard News
> (Kriminalität, Politik), HuffPost = Lifestyle (Entertainment, Gesundheit).*

---

## 4. Slide text — English (for GitHub / portfolio)

### Title slide
> **Media Consumption Analysis**
> Content strategy on a data foundation
>
> 1.45M headlines · 2 sources (ABC News & HuffPost) · 2003–2022 (20 years) · 6 key questions

### Closing slide — methodological notes
> **Transparent notes on methodology**
> - ABC provides headlines only; categories were derived by keyword matching.
>   **60 % remain "Other"** — ABC distribution figures describe the classified 40 %.
> - The source comparison uses only the shared period and shared categories,
>   normalised to 100 % per source.
> - HuffPost politics is reliably tracked only from 2014 — read the trend from 2014 on.
> - Data is intentionally pre-aggregated for a fast, interactive dashboard.
>
> *Despite these limits the core patterns are stable: ABC = hard news
> (crime, politics), HuffPost = lifestyle (entertainment, health).*

---

## 5. Files in this project

| File | Purpose |
|---|---|
| `01_tableau_aggregiert.csv` | Article counts & word lengths per source/year/month/category — distribution, trend, seasonality, length |
| `02_tableau_keywords.csv` | Top keywords per category & source — keyword analysis |
| `03_tableau_autoren.csv` | Articles per author & category (HuffPost) — source analysis |
| `04_tableau_vergleich.csv` | Topic share ABC vs. HuffPost, shared categories — source comparison |
| `kategorie_summary.csv` | ABC category distribution summary |
| `VS_quellenvergleich.csv` | Source comparison (long form) |
| `00_kategorie_mapping.csv` | Documents the label harmonisation applied across all files |
| `Tableau_Bauanleitung.pdf` | Step-by-step build guide (6 sheets → 1 dashboard) |

All category labels were harmonised to a single canonical vocabulary; see
`00_kategorie_mapping.csv`. Article totals are unchanged by the harmonisation
(1,244,182 ABC articles before and after), confirming no data loss.
