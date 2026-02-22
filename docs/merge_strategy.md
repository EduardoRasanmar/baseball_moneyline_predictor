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
