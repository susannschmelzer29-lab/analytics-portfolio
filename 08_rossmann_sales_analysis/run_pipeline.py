"""
Headless runner: executes the analysis notebook and generates all CSVs in ./output.
Called as the Docker default (CMD in the Dockerfile).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
NOTEBOOK = PROJECT_DIR / "rossmann_sales_analysis.ipynb"
OUTPUT_DIR = PROJECT_DIR / "output"


def get_notebook_path() -> Path:
    return NOTEBOOK


def get_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def main():
    print(f"[run_pipeline] Running {NOTEBOOK.name} from {PROJECT_DIR} ...", flush=True)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            "--output-dir",
            str(PROJECT_DIR),
            "--output",
            "executed.ipynb",
            str(NOTEBOOK),
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_DIR),
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    get_output_dir()
    print(f"[run_pipeline] Done. Results are in {OUTPUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
