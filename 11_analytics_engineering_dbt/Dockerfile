FROM python:3.12-slim

RUN useradd --create-home --shell /bin/bash analyst
WORKDIR /project

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=analyst:analyst . .
USER analyst

ENV DBT_PROFILES_DIR=/project/dbt

# Full run: regenerate data, build models, run every test.
CMD ["sh", "-c", "python scripts/generate_seeds.py && cd dbt && dbt build"]
