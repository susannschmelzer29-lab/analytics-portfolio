# Projektkontext für Claude Code

## Worum es geht
Rossmann Store Sales EDA als **Portfolio-Projekt** (Data Analyst). Ziel dieses
Arbeitsschritts: **Git und Docker** sauber auf das bestehende Analyse-Notebook
anwenden, damit das Projekt reproduzierbar und als GitHub-Nachweis vorzeigbar ist.
Kandidat für Portfolio-Projekt `08`.

## Umgebung (wichtig!)
- **Windows + PowerShell**, Anaconda (base), VS Code.
- **PowerShell-Befehle immer einzeln geben** — niemals mehrere verketten.
- **Keine Here-Strings** (`@" ... "@`) verwenden — die hängen zuverlässig.
  Dateien direkt schreiben statt via Here-String erzeugen.

## Getroffene Entscheidungen
- **Docker-Default: Pipeline headless** (`run_pipeline.py` führt das Notebook aus,
  erzeugt CSVs in `output/`). **JupyterLab** ist optional per Zusatzbefehl startbar.
- **Rohdaten werden gemountet**, nicht ins Image gebacken. Nur
  `daten/train_sample.csv` (2.000 Zeilen) liegt im Repo.
- Große Dateien (`train.csv` 37 MB, `rossmann_master_tableau.csv` ~165 MB) sind
  per `.gitignore` ausgeschlossen — dürfen **nicht** committet werden
  (GitHub-Limit 100 MB).

## Status
- Notebook läuft **fehlerfrei end-to-end durch** (alle 17 Zellen, Exit 0).
- Alle 13 Output-CSVs werden korrekt erzeugt; Master = 1.017.209 × 34, 0 fehlende
  Store-Merges.
- Bug in `ergebnis_pruefen.py` bereits gefixt (überflüssige `sep=";"`-Zeile
  entfernt, `low_memory=False` ergänzt).

## Noch offen / mögliche nächste Schritte
1. `daten/train.csv` + `store.csv` von Kaggle lokal in `daten/` legen.
2. `git init`, ersten Commit, Repo nach GitHub pushen
   (`susannschmelzer29-lab/analytics-portfolio`, ggf. als Unterordner `08_...`).
3. `docker build -t rossmann-analyse .` lokal testen.
4. Headless-Run + JupyterLab-Run einmal verifizieren (siehe README).
5. Optional: `docker-compose.yml` mit Postgres ergänzen, falls SQL-Teil gewünscht.

## Dateien in diesem Ordner
Dockerfile, .dockerignore, .gitignore, requirements.txt, run_pipeline.py,
ergebnis_pruefen.py, README.md, Rossmann_Analyse_mit_Ergebnissen.ipynb,
daten/train_sample.csv
