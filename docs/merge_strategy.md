# Data Merge Strategy for Baseball Game Winner Prediction

## Overview

Predict **game winners** (binary: home team wins or loses) using pre-game features. The key constraint: features must come from **prior games only**, never from the game being predicted.

---

## File Summary

| File | Rows | Grain | Key Columns |
|------|------|-------|-------------|
| **gameinfo.csv** | 25,193 | 1 row per game | `gid`, `date`, `visteam`, `hometeam`, `wteam`, `lteam`, `vruns`, `hruns`, `season` |
| **teamstats.csv** | 50,386 | 1 row per team per game | `gid`, `team`, `date`, `opp` + batting/pitching stats |
| **batting.csv** | 738,222 | 1 row per player per game | `gid`, `id`, `team`, `date` + batting stats |
| **pitching.csv** | 215,835 | 1 row per pitcher per game | `gid`, `id`, `team`, `date` + pitching stats |
| **fielding.csv** | 686,050 | 1 row per player position per game | `gid`, `id`, `team`, `date` + fielding stats |
| **plays.csv** | 1,988,277 | 1 row per play | `gid`, `date`, `batteam`, `pitteam` + event-level data |
| **allplayers.csv** | 17,275 | 1 row per player per season | `id`, `team`, `season` + games by position |

---

## Recommended Merge Architecture

### Target Table: `gameinfo` (base)

- **Target variable**: `home_win` = 1 if `wteam == hometeam`, else 0  
- **One row per game** (`gid`)

### Feature Sources (all aggregated before game date)

Features should be **rolling averages** over each team’s last N games (e.g. 10–20) as of the day before the game.

---

## Merge Flow

```
gameinfo (base: 1 row/game)
    │
    ├──► teamstats (aggregate by gid, team → team-game stats)
    │         │
    │         └──► Compute rolling: runs, hits, HR, OBP, SLG, ERA, K/9, BB/9, etc.
    │              per team, up to date D-1
    │
    ├──► batting (aggregate by gid, team → team batting per game)
    │         └──► Rolling: team OPS, wOBA-like, K%, BB%, etc.
    │
    ├──► pitching (aggregate by gid, team → team pitching per game)
    │         └──► Rolling: ERA, WHIP, K/9, BB/9
    │
    └──► plays (optional, for advanced metrics)
              └──► Aggregate per game → rolling: run expectancy, clutch, etc.
```

### Merge Keys

| Join | Key | Notes |
|------|-----|-------|
| gameinfo ↔ teamstats | `gid` | teamstats has 2 rows per game; pivot or join on `team = visteam` / `team = hometeam` |
| gameinfo ↔ rolling team stats | `(date, visteam)` and `(date, hometeam)` | Rolling stats computed as of prior games for each team |
| batting/pitching → team-game | `gid` + `team` | Aggregate player stats to team level per game |

---

## Step-by-Step Merge Plan

### 1. Base dataset

- Start from `gameinfo` (all games).
- Create `home_win` from `wteam` and `hometeam`.

### 2. Team-game stats from `teamstats`

- Use `teamstats`: already one row per team per game.
- Per game/team, you have: `b_pa`, `b_ab`, `b_r`, `b_h`, `b_hr`, `b_w`, `b_k`, `p_er`, `p_bfp`, `p_h`, `p_k`, etc.

### 3. Rolling features (critical)

- Sort games by `(team, date)`.
- For each team and date:
  - Take games with `date < current_date`.
  - Compute rolling means (e.g. last 10, 20 games): runs, hits, HR, K, BB, ERA-like metrics.
- Store as `team_rolling_{metric}_last_N`.

### 4. Join to gameinfo

- For each game:
  - Join visitor features on `(date, visteam)`.
  - Join home features on `(date, hometeam)`.
- Use only stats from prior games; exclude the current game.

### 5. Optional: batting and pitching

- Aggregate `batting` and `pitching` by `(gid, team)` to get team totals per game.
- Compute rolling averages as above.
- Join visitor/home rolling stats on `(date, visteam)` and `(date, hometeam)`.

### 6. Optional: plays

- Aggregate `plays` by `gid` (e.g. run expectancy, base-out state, clutch situations).
- Build rolling team metrics from these.
- Add as extra features if useful.

### 7. Optional: allplayers

- Use for roster / lineup strength (e.g. prior-season WAR) or platoon splits.
- Lower priority for a first model.

---

## Feature Selection Rationale

### Why teamstats only (not batting, pitching, fielding, or plays)?

- **teamstats** already has team-level totals per game: one row per team per game with batting, pitching, and fielding aggregates. No aggregation step needed.
- **batting.csv** and **pitching.csv** are player-level; we’d need to sum by `(gid, team)` to get team stats, which duplicates teamstats.
- **plays.csv** is event-level; useful for advanced metrics (run expectancy, clutch) but adds complexity and extra processing.
- **allplayers.csv** is player-season level; useful for roster strength or platoon splits but requires more joins and logic.

Using **teamstats** alone gives a simple, low-friction pipeline. Other sources can be added later if they improve performance.

### Why these batting metrics?

- **Runs** — Direct outcome; most predictive of scoring.
- **Hits, HR, walks, strikeouts** — Core components of run production and plate discipline.
- **OBP, SLG, OPS** — Standard summaries of hitting; OPS is strongly correlated with runs.
- **Stolen bases** — Small but meaningful indicator of aggressiveness and baserunning.

### Why these pitching metrics?

- **ERA** — Standard measure of run prevention.
- **WHIP** — Baserunners per inning; predictive of scoring allowed.
- **K/9, BB/9, HR/9** — Components of ERA; stable over short windows.

### Why errors (fielding)?

- **Errors** — Reflect defensive quality and “extra outs” given to opponents; cheap to compute from teamstats.

### Why difference features (home − visitor)?

- Comparing home vs visitor stats reduces multicollinearity and directly encodes “who is favored.”
- A single `diff_runs_avg10` often outperforms separate `vis_runs` and `home_runs` because it captures relative strength.

### Why rolling window of 10?

- Balances recency (last 10 games) with sample size.
- 10 games ≈ two weeks; captures short-term form without excessive noise.
- Early-season games have fewer prior games; those rows get NaN or partial windows.

### Why daynight, temp, windspeed?

- **Daynight** — Park and visibility effects; different run environments.
- **Temp** — Warm weather tends to favor offense.
- **Windspeed** — Affects fly balls in some parks.

### What was excluded (for now)?

- **batting/pitching** — Redundant with teamstats for team totals.
- **plays** — Useful for run expectancy, leverage, etc., but adds complexity.
- **allplayers** — Roster/lineup strength is a later iteration.
- **Doubles, triples** — SLG already incorporates them.
- **Sacrifice hits/flies, HBP, IBB** — Minor; OBP and OPS capture most of the effect.
- **Defensive stats beyond errors** — Po, assists, double plays are noisier and less predictive than errors over short windows.

---

## Resulting Schema (conceptual)

| Column | Source |
|--------|--------|
| gid, date, visteam, hometeam, season | gameinfo |
| home_win | derived from wteam, hometeam |
| vis_runs_avg_10, vis_hits_avg_10, vis_hr_avg_10, ... | teamstats rolling |
| home_runs_avg_10, home_hits_avg_10, home_hr_avg_10, ... | teamstats rolling |
| vis_era_avg_10, home_era_avg_10, ... | teamstats rolling |
| vis_obp_avg_10, home_obp_avg_10, ... | batting aggregate → rolling |
| diff_runs_10 (= home - vis), diff_era_10, ... | derived |

---

## Implementation Notes

1. **Ordering**: Ensure games are sorted by `(team, date)` before computing rolling stats.
2. **Cold start**: Early-season games have few prior games; use expanding windows or treat first N games as missing/separate.
3. **Pandas**: Use `groupby(team)` + `shift()` or `rolling()` to avoid leakage.
4. **Memory**: `teamstats` is small; rolling features can be computed in memory. For batting/pitching/plays, use chunking if needed.
5. **Alignment**: Rolling features are indexed by `(date, team)`. Join to `gameinfo` on `(date, visteam)` and `(date, hometeam)`.

---

## Minimal viable merge (start here)

1. Use **gameinfo** as base and create `home_win`.
2. Use **teamstats** only to compute team rolling stats (runs, hits, HR, ERA).
3. Join visitor and home rolling features to gameinfo.
4. Fit a simple model (e.g. logistic regression or XGBoost) on `home_win`.
5. Iterate by adding batting/pitching aggregates and plays-based metrics if they improve performance.
