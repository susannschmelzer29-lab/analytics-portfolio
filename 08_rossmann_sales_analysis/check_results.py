from __future__ import annotations

from pathlib import Path

import pandas as pd


def get_master_csv_path() -> Path:
    project_dir = Path(__file__).resolve().parent
    return project_dir / "output" / "rossmann_master_tableau.csv"


def main() -> None:
    csv_path = get_master_csv_path()
    df = pd.read_csv(csv_path, low_memory=False)

    print("Shape (rows, columns):", df.shape)
    print("\nColumns:")
    print(df.columns.tolist())
    print("\nFirst rows:")
    print(df.head(10))
    print("\nInfo:")
    print(df.info())


if __name__ == "__main__":
    main()
