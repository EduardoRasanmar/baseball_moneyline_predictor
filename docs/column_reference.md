# Model Data Column Reference

Reference for all columns in `data/model_data.csv`. Each row represents one game.

---

## Game Identifiers

| Column | Description |
|--------|-------------|
| **gid** | Retrosheet game ID (e.g. CHN201504050 = CHC home game on 2015-04-05, game 0) |
| **date** | Game date in YYYYMMDD format |
| **visteam** | Visiting team abbreviation (e.g. SLN, SFN) |
| **hometeam** | Home team abbreviation (e.g. CHN, ARI) |
| **site** | Retrosheet park code (e.g. CHI11, PHO01) |
| **season** | Year of the season (e.g. 2015) |

---

## Game Metadata (from Retrosheet gameinfo)

| Column | Description |
|--------|-------------|
| **number** | Game number (0 = first game of day, 1 = second in doubleheader, etc.) |
| **starttime** | Scheduled start time (e.g. 7:17PM) |
| **daynight** | Encoded: 1 = day game, 0 = night game |
| **innings** | Number of innings played |
| **tiebreaker** | Whether game used extra-inning runner rule |
| **usedh** | Designated hitter used (True/False) |
| **htbf** | Length of game ( pitches or batters faced; varies by source) |
| **timeofgame** | Game duration in minutes |
| **attendance** | Reported attendance |
| **fieldcond** | Field condition (unknown, dry, wet, etc.) |
| **precip** | Precipitation (unknown, none, drizzle, etc.) |
| **sky** | Sky conditions (unknown, sunny, cloudy, overcast, dome, etc.) |
| **temp** | Temperature in Fahrenheit |
| **winddir** | Wind direction (e.g. fromcf, ltor) |
| **windspeed** | Wind speed (mph) |
| **oscorer** | Official scorer ID |
| **forfeit** | Game forfeited |
| **suspend** | Game suspended |
| **umphome**, **ump1b**, **ump2b**, **ump3b**, **umplf**, **umprf** | Umpire IDs by position |
| **wp**, **lp**, **save** | Winning pitcher, losing pitcher, save (pitcher IDs) |
| **gametype** | regular, playoff, etc. |
| **vruns** | Visitor runs (final score) |
| **hruns** | Home runs (final score) |
| **wteam** | Winning team abbreviation |
| **lteam** | Losing team abbreviation |
| **line**, **batteries**, **lineups**, **box**, **pbp** | Retrosheet metadata flags |

---

## Target Variable

| Column | Description |
|--------|-------------|
| **home_win** | 1 if home team won, 0 if visitor won. Primary target for prediction. |

---

## User-Requested Features (aliases)

These match the requested `FEATURE_COLS` naming (away = visitor).

| Column | Description |
|--------|-------------|
| **home_rolling_avg_wins_10** | Home team: win rate in last 10 games (0–1) |
| **away_rolling_avg_wins_10** | Visitor: win rate in last 10 games |
| **home_rolling_avg_runs_10** | Home: runs scored per game (alias of home_b_r_avg10) |
| **away_rolling_avg_runs_10** | Visitor: runs scored per game |
| **home_rolling_avg_runs_allowed_10** | Home: runs allowed per game (p_r) |
| **away_rolling_avg_runs_allowed_10** | Visitor: runs allowed per game |
| **home_rolling_avg_run_diff_10** | Home: run differential (runs scored − runs allowed) per game |
| **away_rolling_avg_run_diff_10** | Visitor: run differential per game |
| **home_rolling_avg_h2h_wins_10** | Home team’s win rate in last 10 head-to-head games vs opponent |
| **away_rolling_avg_h2h_wins_10** | Visitor’s win rate in last 10 H2H games |
| **home_rest_days** | Days since home team’s last game (0 = same day / doubleheader) |
| **away_rest_days** | Days since visitor’s last game |
| **home_pitcher_rolling_wins_centered_10** | Starting pitcher’s win rate in last 10 starts − 0.5 (centered at .500) |
| **vis_pitcher_rolling_wins_centered_10** | Visitor’s starter: same metric |

---

## Rolling Batting Features (10-game average, prior games only)

All `*_avg10` columns are the average of that team's last 10 games **before** the current game.

| Column | Description |
|--------|-------------|
| **vis_win_avg10** | Visitor: win rate (1 = win, 0 = loss) per game |
| **vis_b_r_avg10** | Visitor: runs per game |
| **vis_b_h_avg10** | Visitor: hits per game |
| **vis_b_hr_avg10** | Visitor: home runs per game |
| **vis_b_w_avg10** | Visitor: walks per game |
| **vis_b_k_avg10** | Visitor: strikeouts per game |
| **vis_b_sb_avg10** | Visitor: stolen bases per game |
| **vis_obp_avg10** | Visitor: on-base percentage = (H + BB + HBP) / PA |
| **vis_slg_avg10** | Visitor: slugging percentage = (1B + 2×2B + 3×3B + 4×HR) / AB |
| **vis_ops_avg10** | Visitor: OPS = OBP + SLG |
| **home_b_r_avg10** | Home: runs per game |
| **home_b_h_avg10** | Home: hits per game |
| **home_b_hr_avg10** | Home: home runs per game |
| **home_b_w_avg10** | Home: walks per game |
| **home_b_k_avg10** | Home: strikeouts per game |
| **home_b_sb_avg10** | Home: stolen bases per game |
| **home_obp_avg10** | Home: on-base percentage |
| **home_slg_avg10** | Home: slugging percentage |
| **home_ops_avg10** | Home: OPS |
| **vis_run_diff_avg10** | Visitor: run differential (runs scored − runs allowed) per game |
| **home_run_diff_avg10** | Home: run differential per game |

---

## Rolling Pitching Features (10-game average, prior games only)

| Column | Description |
|--------|-------------|
| **vis_p_r_avg10** | Visitor: runs allowed per game (total, not just earned) |
| **home_p_r_avg10** | Home: runs allowed per game |
| **vis_p_er_avg10** | Visitor: earned runs allowed per game (raw) |
| **vis_p_h_avg10** | Visitor: hits allowed per game |
| **vis_p_hr_avg10** | Visitor: home runs allowed per game |
| **vis_p_w_avg10** | Visitor: walks allowed per game |
| **vis_p_k_avg10** | Visitor: strikeouts per game |
| **vis_era_avg10** | Visitor: ERA (earned runs per 9 innings) |
| **vis_whip_avg10** | Visitor: WHIP = (H + BB) per inning |
| **vis_k9_avg10** | Visitor: strikeouts per 9 innings |
| **vis_bb9_avg10** | Visitor: walks per 9 innings |
| **vis_hr9_avg10** | Visitor: home runs allowed per 9 innings |
| **home_p_er_avg10** | Home: earned runs allowed per game (raw) |
| **home_p_h_avg10** | Home: hits allowed per game |
| **home_p_hr_avg10** | Home: home runs allowed per game |
| **home_p_w_avg10** | Home: walks allowed per game |
| **home_p_k_avg10** | Home: strikeouts per game |
| **home_era_avg10** | Home: ERA |
| **home_whip_avg10** | Home: WHIP |
| **home_k9_avg10** | Home: strikeouts per 9 innings |
| **home_bb9_avg10** | Home: walks per 9 innings |
| **home_hr9_avg10** | Home: home runs allowed per 9 innings |

---

## Rolling Fielding Features (10-game average, prior games only)

| Column | Description |
|--------|-------------|
| **vis_d_e_avg10** | Visitor: errors per game |
| **home_d_e_avg10** | Home: errors per game |

---

## Difference Features (home − visitor)

All `diff_*` columns are `home_*_avg10 − vis_*_avg10`. Positive = home team ahead on that metric.

| Column | Description |
|--------|-------------|
| **diff_win_avg10** | Home − visitor win rate |
| **diff_b_r_avg10** | Home − visitor runs per game |
| **diff_p_r_avg10** | Home − visitor runs allowed (negative = home allows fewer) |
| **diff_run_diff_avg10** | Home − visitor run differential |
| **diff_obp_avg10** | Home − visitor OBP |
| **diff_slg_avg10** | Home − visitor SLG |
| **diff_ops_avg10** | Home − visitor OPS |
| **diff_era_avg10** | Home − visitor ERA (negative = home pitching better) |
| **diff_whip_avg10** | Home − visitor WHIP |
| **diff_k9_avg10** | Home − visitor K/9 |
| **diff_bb9_avg10** | Home − visitor BB/9 |
| **diff_hr9_avg10** | Home − visitor HR/9 |
| **diff_b_h_avg10** | Home − visitor hits per game |
| **diff_b_hr_avg10** | Home − visitor home runs per game |
| **diff_b_w_avg10** | Home − visitor walks per game |
| **diff_b_k_avg10** | Home − visitor strikeouts per game |
| **diff_b_sb_avg10** | Home − visitor stolen bases per game |
| **diff_d_e_avg10** | Home − visitor errors per game (negative = home fewer errors) |

---

## Notes

- Rolling features are NaN for the first ~10 games each team plays in a season (no prior data).
- All rolling metrics use only games **before** the current game to avoid leakage.
- Batting metrics (OBP, SLG, OPS) are computed per game, then averaged over the rolling window.
