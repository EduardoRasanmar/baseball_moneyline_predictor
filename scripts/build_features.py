#!/usr/bin/env python3
"""
Build pre-game features with 10-game rolling averages from teamstats.
Merges onto gameinfo and saves model-ready dataset.
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path("data")
TEAMSTATS_PATH = DATA_DIR / "teamstats.csv"
GAMEINFO_PATH = DATA_DIR / "gameinfo.csv"
OUTPUT_PATH = DATA_DIR / "model_data.csv"

ROLLING_WINDOW = 10


def _safe_divide(a: pd.Series, b: pd.Series) -> pd.Series:
    """Divide a by b, return 0 where b is 0 or NaN."""
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(b > 0, a / b, np.nan)
    return pd.Series(out, index=a.index)


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add OBP, SLG, OPS, ERA, WHIP, K/9, BB/9, HR/9 per game."""
    # Batting
    df = df.copy()
    df["obp"] = _safe_divide(
        df["b_h"] + df["b_w"] + df["b_hbp"],
        df["b_pa"].replace(0, np.nan),
    )
    df["slg"] = _safe_divide(
        df["b_h"] + df["b_d"] + 2 * df["b_t"] + 3 * df["b_hr"],
        df["b_ab"].replace(0, np.nan),
    )
    df["ops"] = df["obp"].fillna(0) + df["slg"].fillna(0)
    # Pitching (innings = p_ipouts / 3)
    innings = df["p_ipouts"] / 3
    innings = innings.replace(0, np.nan)
    df["era"] = _safe_divide(9 * df["p_er"], innings)
    df["whip"] = _safe_divide(df["p_h"] + df["p_w"], innings)
    df["k9"] = _safe_divide(9 * df["p_k"], innings)
    df["bb9"] = _safe_divide(9 * df["p_w"], innings)
    df["hr9"] = _safe_divide(9 * df["p_hr"], innings)
    return df


def compute_rolling_stats(df: pd.DataFrame, window: int = ROLLING_WINDOW) -> pd.DataFrame:
    """
    Compute rolling mean of last `window` games (excluding current game) per team.
    Uses shift(1).rolling(window).mean() to avoid leakage.
    """
    cols_to_roll = [
        "b_r", "b_h", "b_hr", "b_w", "b_k", "b_sb",
        "obp", "slg", "ops",
        "p_er", "p_h", "p_hr", "p_w", "p_k",
        "era", "whip", "k9", "bb9", "hr9",
        "d_e",
    ]
    out = df[["gid", "team", "date"]].copy()

    for col in cols_to_roll:
        if col not in df.columns:
            continue
        out[f"{col}_avg{window}"] = (
            df.groupby("team", sort=False)[col]
            .transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
        )
    return out


def main():
    print("Loading data...")
    teamstats = pd.read_csv(TEAMSTATS_PATH, low_memory=False)
    gameinfo = pd.read_csv(GAMEINFO_PATH, low_memory=False)

    # Ensure numeric
    teamstats["date"] = pd.to_numeric(teamstats["date"], errors="coerce")
    teamstats = teamstats.dropna(subset=["date", "team"])
    teamstats["date"] = teamstats["date"].astype(int)

    # Add derived metrics
    print("Adding derived metrics (OBP, SLG, OPS, ERA, WHIP, K/9, BB/9, HR/9)...")
    teamstats = add_derived_metrics(teamstats)

    # Sort for rolling
    teamstats = teamstats.sort_values(["team", "date"]).reset_index(drop=True)

    # Compute rolling stats (prior 10 games only)
    print(f"Computing {ROLLING_WINDOW}-game rolling averages...")
    rolling = compute_rolling_stats(teamstats, ROLLING_WINDOW)

    # Join on gid so each game gets correct rolling (handles doubleheaders)
    suffix = f"_avg{ROLLING_WINDOW}"
    roll_cols = [c for c in rolling.columns if c.endswith(suffix)]

    vis_features = rolling.rename(
        columns={"team": "visteam", **{c: f"vis_{c}" for c in roll_cols}}
    )[["gid", "visteam"] + [f"vis_{c}" for c in roll_cols]]
    home_features = rolling.rename(
        columns={"team": "hometeam", **{c: f"home_{c}" for c in roll_cols}}
    )[["gid", "hometeam"] + [f"home_{c}" for c in roll_cols]]

    # Merge onto gameinfo
    gameinfo["date"] = pd.to_numeric(gameinfo["date"], errors="coerce")
    df = gameinfo.merge(vis_features, on=["gid", "visteam"], how="left")
    df = df.merge(home_features, on=["gid", "hometeam"], how="left")

    # Target
    df["home_win"] = (df["wteam"] == df["hometeam"]).astype(int)

    # Difference features (home - visitor)
    for base in ["b_r", "obp", "slg", "ops", "era", "whip", "k9", "bb9", "hr9", "b_h", "b_hr", "b_w", "b_k", "b_sb", "d_e"]:
        vc, hc = f"vis_{base}{suffix}", f"home_{base}{suffix}"
        if vc in df.columns and hc in df.columns:
            df[f"diff_{base}{suffix}"] = df[hc].sub(df[vc])

    # Context from gameinfo
    df["daynight"] = df["daynight"].map({"day": 1, "night": 0}).fillna(-1)
    df["temp"] = pd.to_numeric(df["temp"], errors="coerce")
    df["windspeed"] = pd.to_numeric(df["windspeed"], errors="coerce")

    # Save
    df.to_csv(OUTPUT_PATH, index=False)
    n_complete = df[f"vis_b_r{suffix}"].notna().sum()
    print(f"Saved {len(df):,} rows to {OUTPUT_PATH}")
    print(f"Columns: {len(df.columns)}")
    print(f"Rows with rolling features: {n_complete:,} (drop first ~{ROLLING_WINDOW} games/team)")


if __name__ == "__main__":
    main()
