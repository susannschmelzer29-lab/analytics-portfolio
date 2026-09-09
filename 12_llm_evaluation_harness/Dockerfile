FROM python:3.12-slim

RUN useradd --create-home --shell /bin/bash evaluator
WORKDIR /harness

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e ".[dev]"

COPY --chown=evaluator:evaluator . .
USER evaluator

CMD ["sh", "-c", "python -m pytest -q && python scripts/run_eval.py"]
