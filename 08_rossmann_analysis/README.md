# Rossmann Store Sales — Analyse-Pipeline

Explorative Datenanalyse des [Rossmann Store Sales](https://www.kaggle.com/c/rossmann-store-sales)
Datensatzes (1.017.209 Verkaufszeilen, 1.115 Filialen). Die Pipeline beantwortet
sechs strategische Fragestellungen und exportiert vorbereitete CSVs für Tableau.

## Inhalt

| Frage | Output |
|-------|--------|
| Filial-Ranking nach Tagesumsatz | `q1_filial_ranking.csv` |
| Einfluss der Wettbewerbsnähe | `q2_wettbewerb_distanz.csv` |
| Saisonalität (Monat / Wochentag) | `q3_saison_*.csv` |
| Feiertage & Schulferien | `q4_*.csv` |
| Promo-Uplift | `q5_promo*.csv` |
| Filialtyp & Sortiment | `q6_*.csv` |
| Management-KPIs | `kpi_management.csv` |

Zusätzlich: `rossmann_master_tableau.csv` (voller Master-Datensatz, ~165 MB, wird
**nicht** eingecheckt, sondern lokal erzeugt).

## Daten beschaffen

Die Rohdaten sind aus Größengründen nicht im Repo. Nur `daten/train_sample.csv`
(2.000 Zeilen) liegt als Vorschau bei.

1. Daten von Kaggle laden: `train.csv`, `store.csv` (optional `test.csv`).
2. In den Ordner `daten/` legen.

## Lokal ausführen (ohne Docker)

```powershell
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --output executed.ipynb Rossmann_Analyse_mit_Ergebnissen.ipynb
python ergebnis_pruefen.py
```

## Mit Docker

**Image bauen:**

```powershell
docker build -t rossmann-analyse .
```

**Pipeline headless ausführen** (Default — erzeugt alle CSVs in `output/`):

```powershell
docker run --rm -v ${PWD}/daten:/app/daten -v ${PWD}/output:/app/output rossmann-analyse
```

**JupyterLab im Container starten** (Notebook interaktiv im Browser):

```powershell
docker run --rm -p 8888:8888 -v ${PWD}/daten:/app/daten -v ${PWD}/output:/app/output rossmann-analyse jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
```

Danach die im Terminal angezeigte URL (`http://127.0.0.1:8888/lab?token=...`) im Browser öffnen.

## Projektstruktur

```
.
├── Rossmann_Analyse_mit_Ergebnissen.ipynb   # Kern-Analyse
├── run_pipeline.py                          # Headless-Runner (Docker-Default)
├── ergebnis_pruefen.py                      # QA-Check der Master-CSV
├── requirements.txt
├── Dockerfile
├── .dockerignore / .gitignore
├── daten/                                   # Rohdaten (gemountet) + Sample
├── output/                                  # erzeugte CSVs (nicht im Repo)
└── figures/                                 # erzeugte Grafiken (nicht im Repo)
```
