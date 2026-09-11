#!/usr/bin/env python3
"""Install and verify the repaired portfolio projects.

Usage:
    python scripts/verify_portfolio_projects.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = [ROOT / "10_agent_engineering_lab", ROOT / "12_llm_evaluation_harness"]
DBT_PROJECT = ROOT / "11_analytics_engineering_dbt"


def run(cmd: list[str], *, cwd: Path | None = None) -> int:
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd or ROOT), check=False)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        return result.returncode
    return 0


def main() -> int:
    install_cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-e",
        f"{PROJECTS[0]}[dev]",
        "-e",
        f"{PROJECTS[1]}[dev]",
    ]
    test_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "10_agent_engineering_lab/tests",
        "12_llm_evaluation_harness/tests",
    ]

    dbt_install = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-r",
        str(DBT_PROJECT / "requirements.txt"),
    ]
    dbt_verify = [
        sys.executable,
        str(DBT_PROJECT / "scripts" / "verify_dbt_build.py"),
    ]

    rc = run(install_cmd)
    if rc != 0:
        return rc

    rc = run(test_cmd)
    if rc != 0:
        return rc

    rc = run(dbt_install)
    if rc != 0:
        return rc

    return run(dbt_verify)


if __name__ == "__main__":
    raise SystemExit(main())
