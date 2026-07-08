"""
Headless-Runner: führt das Analyse-Notebook aus und erzeugt alle CSVs in ./output.
Wird als Docker-Default aufgerufen (CMD im Dockerfile).
"""
import subprocess
import sys

NOTEBOOK = "Rossmann_Analyse_mit_Ergebnissen.ipynb"

def main():
    print(f"[run_pipeline] Führe {NOTEBOOK} aus ...", flush=True)
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
    print("[run_pipeline] Fertig. Ergebnisse liegen in ./output", flush=True)

if __name__ == "__main__":
    main()
