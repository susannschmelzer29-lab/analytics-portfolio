# Build and test environment.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends jq \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash agent
WORKDIR /work

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e ".[dev]"

COPY --chown=agent:agent . .
USER agent

CMD ["python", "-m", "pytest"]
