FROM python:3.11-slim

# System packages required by matplotlib/pandas
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Project code
COPY controlling_kpi_analysis.ipynb .
COPY check_results.py .
COPY run_pipeline.py .

# Folders for mounted data and generated outputs
RUN mkdir -p /app/data /app/output /app/figures

# Default: run the pipeline headless -> generates CSVs in /app/output
CMD ["python", "run_pipeline.py"]

# JupyterLab alternative (see README):
#   docker run -p 8888:8888 -v ${PWD}/data:/app/data controlling-kpi-analysis \
#     jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
