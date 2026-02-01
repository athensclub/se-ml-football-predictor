#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["pandas", "pyarrow"]
# ///
"""Ingest FIFA CSV(s) and write a canonical player table to Parquet.

Output:
- data/cache/fifa_players.parquet
"""
from pathlib import Path
import pandas as pd

FOLDER = Path("data") / "fifa23"
OUT = Path("data") / "cache"
OUT.mkdir(parents=True, exist_ok=True)

CSV_CANDIDATES = ["male_players.csv", "male_players (legacy).csv", "female_players.csv"]

DEFAULT_COLS = [
    "sofifa_id",
    "short_name",
    "long_name",
    "player_positions",
    "overall",
    "age",
    "nationality",
    "club",
    "pace",
    "shooting",
    "passing",
    "dribbling",
    "defending",
    "physic",
]


def find_csv():
    for c in CSV_CANDIDATES:
        p = FOLDER / c
        if p.exists():
            return p
    raise FileNotFoundError("No FIFA CSV found in data/fifa23/ (searched candidates)")


def load_and_select(path: Path):
    # read a small chunk to inspect columns
    sample = pd.read_csv(path, nrows=100)
    available = set(sample.columns)
    cols = [c for c in DEFAULT_COLS if c in available]
    if not cols:
        raise RuntimeError("None of the default columns found in FIFA CSV; available columns: " + ",".join(list(available)[:20]))
    print("Selected columns:", cols)
    df = pd.read_csv(path, usecols=cols)
    # normalize column names
    df = df.rename(columns={
        col: col for col in cols
    })
    return df


def main():
    path = find_csv()
    print("Loading FIFA CSV:", path)
    df = load_and_select(path)
    out = OUT / "fifa_players.parquet"
    try:
        df.to_parquet(out, index=False)
        print("Wrote FIFA players to", out)
    except Exception as e:
        out_csv = OUT / "fifa_players.csv"
        df.to_csv(out_csv, index=False)
        print("Parquet write failed (fallback to CSV). Wrote FIFA players to", out_csv)
        print("Error was:", e)


if __name__ == '__main__':
    main()
