#!/usr/bin/env python3
"""Generate the seed data and run the dbt build for project 11."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DBT_PROJECT_DIR = PROJECT_DIR / "dbt"


def find_dbt_executable() -> str:
    dbt = shutil.which("dbt")
    if dbt:
        return dbt

    appdata = Path.home() / "AppData" / "Roaming" / "Python"
    candidates = sorted(appdata.glob("**/Scripts/dbt.exe"))
    if candidates:
        return str(candidates[-1])

    local = Path.home() / "AppData" / "Local" / "Programs" / "Python"
    candidates = sorted(local.glob("**/Scripts/dbt.exe"))
    if candidates:
        return str(candidates[-1])

    raise FileNotFoundError(
        "dbt executable not found. Install the project requirements and ensure 'dbt' is on PATH."
    )


def run(cmd: list[str], *, cwd: Path | None = None) -> int:
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd or PROJECT_DIR), check=False)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        return result.returncode
    return 0


def main() -> int:
    seed_cmd = [sys.executable, "scripts/generate_seeds.py"]
    dbt_cmd = [
        find_dbt_executable(),
        "build",
        "--project-dir",
        str(DBT_PROJECT_DIR),
        "--profiles-dir",
        str(DBT_PROJECT_DIR),
    ]

    rc = run(seed_cmd, cwd=PROJECT_DIR)
    if rc != 0:
        return rc

    return run(dbt_cmd, cwd=PROJECT_DIR)


if __name__ == "__main__":
    raise SystemExit(main())
