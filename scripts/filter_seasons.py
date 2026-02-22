#!/usr/bin/env python3
"""Filter Retrosheet CSV files to latest 10 seasons (2015-2024)."""

import pandas as pd
from pathlib import Path

DATA_REGULAR = Path("data/regular")
DATA_OUT = Path("data")
MIN_YEAR = 2015

FILES_WITH_DATE = ["teamstats.csv", "pitching.csv", "fielding.csv", "batting.csv", "plays.csv"]
FILES_WITH_SEASON = ["gameinfo.csv", "allplayers.csv"]


def filter_by_date(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """Filter rows where date (YYYYMMDD) year >= 2015."""
    df[date_col] = pd.to_numeric(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    df["_year"] = (df[date_col] // 10000).astype(int)
    return df[df["_year"] >= MIN_YEAR].drop(columns=["_year"])


def filter_by_season(df: pd.DataFrame, season_col: str = "season") -> pd.DataFrame:
    """Filter rows where season >= 2015."""
    df[season_col] = pd.to_numeric(df[season_col], errors="coerce")
    df = df.dropna(subset=[season_col])
    return df[df[season_col] >= MIN_YEAR]


def main():
    DATA_OUT.mkdir(parents=True, exist_ok=True)

    for fname in FILES_WITH_DATE:
        src = DATA_REGULAR / fname
        dst = DATA_OUT / fname
        print(f"Processing {fname}...")
        if fname in ("batting.csv", "plays.csv"):
            chunks = []
            for chunk in pd.read_csv(src, chunksize=500_000, low_memory=False):
                filtered = filter_by_date(chunk)
                if len(filtered) > 0:
                    chunks.append(filtered)
            if chunks:
                pd.concat(chunks, ignore_index=True).to_csv(dst, index=False)
            total_rows = sum(len(c) for c in chunks)
            print(f"  -> {dst} ({total_rows:,} rows)")
        else:
            df = pd.read_csv(src, low_memory=False)
            filtered = filter_by_date(df)
            filtered.to_csv(dst, index=False)
            print(f"  -> {dst} ({len(filtered):,} rows)")

    for fname in FILES_WITH_SEASON:
        src = DATA_REGULAR / fname
        dst = DATA_OUT / fname
        print(f"Processing {fname}...")
        df = pd.read_csv(src, low_memory=False)
        filtered = filter_by_season(df)
        filtered.to_csv(dst, index=False)
        print(f"  -> {dst} ({len(filtered):,} rows)")

    print("Done.")


if __name__ == "__main__":
    main()
