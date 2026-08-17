"""
Headless runner: executes the controlling notebook and generates all CSVs in
./output. Called as the Docker default (CMD in the Dockerfile).
"""
import subprocess
import sys

NOTEBOOK = "controlling_kpi_analysis.ipynb"

def main():
    print(f"[run_pipeline] Running {NOTEBOOK} ...", flush=True)
    result = subprocess.run(
        [
            "jupyter", "nbconvert",
            "--to", "notebook",
            "--execute",
            "--output", "executed.ipynb",
            NOTEBOOK,
        ],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    print("[run_pipeline] Done. Results are in ./output", flush=True)

if __name__ == "__main__":
    main()
