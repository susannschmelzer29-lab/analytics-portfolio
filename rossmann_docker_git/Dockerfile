FROM python:3.11-slim

# Systempakete für matplotlib/pandas
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Abhängigkeiten zuerst (besseres Layer-Caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Projektcode
COPY Rossmann_Analyse_mit_Ergebnissen.ipynb .
COPY ergebnis_pruefen.py .
COPY run_pipeline.py .

# Ordner für gemountete Daten und erzeugte Outputs
RUN mkdir -p /app/daten /app/output /app/figures

# Standard: Pipeline headless ausführen -> erzeugt CSVs in /app/output
CMD ["python", "run_pipeline.py"]

# JupyterLab-Alternative (siehe README):
#   docker run -p 8888:8888 -v ${PWD}/daten:/app/daten rossmann-analyse \
#     jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
