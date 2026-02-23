#!/usr/bin/env python3
"""
Build pre-game features with 10-game rolling averages from teamstats.
Merges onto gameinfo and saves model-ready dataset.
Adds: wins, runs_allowed, run_diff, rest_days, h2h_wins, pitcher_rolling_wins.
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path("data")
TEAMSTATS_PATH = DATA_DIR / "teamstats.csv"
GAMEINFO_PATH = DATA_DIR / "gameinfo.csv"
PITCHING_PATH = DATA_DIR / "pitching.csv"
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
    # Runs allowed (p_r) and run differential
    df["run_diff"] = df["b_r"] - df["p_r"]
    return df


def compute_rolling_stats(df: pd.DataFrame, window: int = ROLLING_WINDOW) -> pd.DataFrame:
    """
    Compute rolling mean of last `window` games (excluding current game) per team.
    Uses shift(1).rolling(window).mean() to avoid leakage.
    """
    cols_to_roll = [
        "win", "b_r", "p_r", "run_diff",
        "b_h", "b_hr", "b_w", "b_k", "b_sb",
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
    for base in ["win", "b_r", "p_r", "run_diff", "obp", "slg", "ops", "era", "whip", "k9", "bb9", "hr9", "b_h", "b_hr", "b_w", "b_k", "b_sb", "d_e"]:
        vc, hc = f"vis_{base}{suffix}", f"home_{base}{suffix}"
        if vc in df.columns and hc in df.columns:
            df[f"diff_{base}{suffix}"] = df[hc].sub(df[vc])

    # Context from gameinfo
    df["daynight"] = df["daynight"].map({"day": 1, "night": 0}).fillna(-1)
    df["temp"] = pd.to_numeric(df["temp"], errors="coerce")
    df["windspeed"] = pd.to_numeric(df["windspeed"], errors="coerce")

    # --- Rest days ---
    gi = gameinfo.copy()
    gi["date"] = pd.to_numeric(gi["date"], errors="coerce")
    gi = gi.sort_values(["date", "gid"])
    vis_rows = gi[["gid", "date", "visteam"]].assign(role="vis")
    home_rows = gi[["gid", "date", "hometeam"]].assign(role="home")
    vis_rows = vis_rows.rename(columns={"visteam": "team"})
    home_rows = home_rows.rename(columns={"hometeam": "team"})
    team_games = pd.concat([vis_rows, home_rows], ignore_index=True)
    team_games = team_games.sort_values(["team", "date", "gid"])
    team_games["prev_date"] = team_games.groupby("team")["date"].shift(1)
    team_games["rest_days"] = np.where(
        team_games["prev_date"].isna(),
        np.nan,
        np.where(team_games["date"] == team_games["prev_date"], 0, team_games["date"] - team_games["prev_date"])
    )
    rest_vis = team_games[team_games["role"] == "vis"][["gid", "team", "rest_days"]].rename(
        columns={"team": "visteam", "rest_days": "vis_rest_days"}
    )
    rest_home = team_games[team_games["role"] == "home"][["gid", "team", "rest_days"]].rename(
        columns={"team": "hometeam", "rest_days": "home_rest_days"}
    )
    df = df.merge(rest_vis, on=["gid", "visteam"], how="left")
    df = df.merge(rest_home, on=["gid", "hometeam"], how="left")
    df["away_rest_days"] = df["vis_rest_days"]

    # --- H2H wins (last 10 matchups between these two teams) ---
    gi_sorted = gi.sort_values("date").reset_index(drop=True)
    h2h_home = []
    h2h_vis = []
    for idx, row in gi_sorted.iterrows():
        d, v, h = row["date"], row["visteam"], row["hometeam"]
        prior = gi_sorted[(gi_sorted["date"] < d) & (
            ((gi_sorted["visteam"] == v) & (gi_sorted["hometeam"] == h)) |
            ((gi_sorted["visteam"] == h) & (gi_sorted["hometeam"] == v))
        )].tail(10)
        if len(prior) == 0:
            h2h_home.append(np.nan)
            h2h_vis.append(np.nan)
            continue
        home_wins = (
            ((prior["visteam"] == h) & (prior["wteam"] == h)) |
            ((prior["hometeam"] == h) & (prior["wteam"] == h))
        ).sum()
        vis_wins = len(prior) - home_wins
        h2h_home.append(home_wins / len(prior))
        h2h_vis.append(vis_wins / len(prior))
    df["home_rolling_avg_h2h_wins_10"] = h2h_home
    df["away_rolling_avg_h2h_wins_10"] = h2h_vis

    # --- Pitcher rolling wins centered (starting pitcher, last 10 starts) ---
    pit = pd.read_csv(PITCHING_PATH, low_memory=False)
    pit["date"] = pd.to_numeric(pit["date"], errors="coerce")
    starters = pit[pit["p_seq"] == 1][["gid", "team", "id", "date"]].copy()
    gi_pit = gameinfo[["gid", "wteam"]].copy()
    starters = starters.merge(gi_pit, on="gid", how="left")
    starters["pitcher_win"] = (starters["wteam"] == starters["team"]).astype(int)
    starters = starters.sort_values(["id", "date"])
    starters["pitcher_wins_avg10"] = (
        starters.groupby("id")["pitcher_win"]
        .transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
    )
    starters["pitcher_wins_centered_10"] = starters["pitcher_wins_avg10"] - 0.5
    pit_vis = starters.rename(columns={"team": "visteam", "pitcher_wins_centered_10": "vis_pitcher_rolling_wins_centered_10"})[
        ["gid", "visteam", "vis_pitcher_rolling_wins_centered_10"]
    ]
    pit_home = starters.rename(columns={"team": "hometeam", "pitcher_wins_centered_10": "home_pitcher_rolling_wins_centered_10"})[
        ["gid", "hometeam", "home_pitcher_rolling_wins_centered_10"]
    ]
    df = df.merge(pit_vis, on=["gid", "visteam"], how="left")
    df = df.merge(pit_home, on=["gid", "hometeam"], how="left")

    # Aliases for user-requested names (away = vis)
    df["away_rolling_avg_wins_10"] = df[f"vis_win{suffix}"]
    df["home_rolling_avg_wins_10"] = df[f"home_win{suffix}"]
    df["away_rolling_avg_runs_10"] = df[f"vis_b_r{suffix}"]
    df["home_rolling_avg_runs_10"] = df[f"home_b_r{suffix}"]
    df["away_rolling_avg_runs_allowed_10"] = df[f"vis_p_r{suffix}"]
    df["home_rolling_avg_runs_allowed_10"] = df[f"home_p_r{suffix}"]
    df["away_rolling_avg_run_diff_10"] = df[f"vis_run_diff{suffix}"]
    df["home_rolling_avg_run_diff_10"] = df[f"home_run_diff{suffix}"]

    # Save
    df.to_csv(OUTPUT_PATH, index=False)
    n_complete = df[f"vis_b_r{suffix}"].notna().sum()
    print(f"Saved {len(df):,} rows to {OUTPUT_PATH}")
    print(f"Columns: {len(df.columns)}")
    print(f"Rows with rolling features: {n_complete:,} (drop first ~{ROLLING_WINDOW} games/team)")


if __name__ == "__main__":
    main()
