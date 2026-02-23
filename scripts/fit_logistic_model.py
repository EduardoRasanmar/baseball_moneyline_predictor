"""
Fit a logistic regression model to predict home team win (home_win).
Uses a season-based train/test split: train on earlier seasons, test on holdout season(s).
"""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "results" / "models"

FEATURED_CSV = DATA_DIR / "model_data.csv"
TEST_SEASONS = [2025]

FEATURE_COLS = [
    # Core (wins, runs, run diff, runs allowed)
    "home_rolling_avg_wins_10",
    "away_rolling_avg_wins_10",
    "home_rolling_avg_runs_10",
    "away_rolling_avg_runs_10",
    "home_rolling_avg_runs_allowed_10",
    "away_rolling_avg_runs_allowed_10",
    "home_rolling_avg_run_diff_10",
    "away_rolling_avg_run_diff_10",
    # H2H, rest, pitcher
    "home_rolling_avg_h2h_wins_10",
    "away_rolling_avg_h2h_wins_10",
    "home_rest_days",
    "away_rest_days",
    "home_pitcher_rolling_wins_centered_10",
    "vis_pitcher_rolling_wins_centered_10",  # away = visitor
    # Rolling batting (hits, HR, BB, K, SB, OBP, SLG, OPS)
    "vis_b_h_avg10", "home_b_h_avg10",
    "vis_b_hr_avg10", "home_b_hr_avg10",
    "vis_b_w_avg10", "home_b_w_avg10",
    "vis_b_k_avg10", "home_b_k_avg10",
    "vis_b_sb_avg10", "home_b_sb_avg10",
    "vis_obp_avg10", "home_obp_avg10",
    "vis_slg_avg10", "home_slg_avg10",
    "vis_ops_avg10", "home_ops_avg10",
    # Rolling pitching (ERA, WHIP, K/9, BB/9, HR/9, hits/walks allowed)
    "vis_era_avg10", "home_era_avg10",
    "vis_whip_avg10", "home_whip_avg10",
    "vis_k9_avg10", "home_k9_avg10",
    "vis_bb9_avg10", "home_bb9_avg10",
    "vis_hr9_avg10", "home_hr9_avg10",
    # Rolling fielding
    "vis_d_e_avg10", "home_d_e_avg10",
    # Difference features (home - visitor)
    "diff_win_avg10", "diff_b_r_avg10", "diff_p_r_avg10", "diff_run_diff_avg10",
    "diff_obp_avg10", "diff_slg_avg10", "diff_ops_avg10",
    "diff_era_avg10", "diff_whip_avg10", "diff_k9_avg10", "diff_bb9_avg10", "diff_hr9_avg10",
    "diff_b_h_avg10", "diff_b_hr_avg10", "diff_b_w_avg10", "diff_b_k_avg10", "diff_b_sb_avg10", "diff_d_e_avg10",
    # Context
    "daynight", "temp", "windspeed",
]
TARGET_COL = "home_win"


def load_and_prepare() -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Load featured CSV, drop rows with missing features, sort by date. Return X, y, season."""
    df = pd.read_csv(FEATURED_CSV, low_memory=False)
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    df["date"] = pd.to_numeric(df["date"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)

    for c in ["home_rest_days", "away_rest_days"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df = df.dropna(subset=FEATURE_COLS)
    X = df[[c for c in FEATURE_COLS if c in df.columns]].astype(float)
    y = df[TARGET_COL].astype(int)
    season = df["season"]
    return X, y, season


def season_split(
    X: pd.DataFrame, y: pd.Series, season: pd.Series, test_seasons: list[int]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split by season: train on seasons not in test_seasons, test on test_seasons."""
    train_mask = ~season.isin(test_seasons)
    test_mask = season.isin(test_seasons)
    return X[train_mask], X[test_mask], y[train_mask], y[test_mask]


def main():
    print(f"Loading {FEATURED_CSV}...")
    X, y, season = load_and_prepare()
    feat_cols = [c for c in FEATURE_COLS if c in X.columns]
    X = X[feat_cols]
    print(f"  Samples: {len(X)}, features: {len(feat_cols)}")

    X_train, X_test, y_train, y_test = season_split(X, y, season, TEST_SEASONS)
    print(f"  Train: {len(y_train)} (seasons not in {TEST_SEASONS}), test: {len(y_test)} (seasons {TEST_SEASONS})")

    if len(y_test) == 0:
        print("  No test data for holdout seasons; fitting on full data without evaluation.")
        X_train, y_train = X, y

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test) if len(y_test) > 0 else X_train_s

    print("\nFitting logistic regression...")
    model = LogisticRegression(max_iter=5000, solver="saga", random_state=42)
    model.fit(X_train_s, y_train)

    train_pred = model.predict(X_train_s)
    train_prob = model.predict_proba(X_train_s)[:, 1]
    train_acc = accuracy_score(y_train, train_pred)
    train_auc = roc_auc_score(y_train, train_prob)
    print(f"  Train accuracy: {train_acc:.4f}")
    print(f"  Train ROC-AUC:  {train_auc:.4f}")

    if len(y_test) > 0:
        y_pred = model.predict(X_test_s)
        y_prob = model.predict_proba(X_test_s)[:, 1]
        acc = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)
        print(f"  Test accuracy: {acc:.4f}")
        print(f"  Test ROC-AUC:  {auc:.4f}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODELS_DIR / "logistic_regression.pkl")
    joblib.dump(
        {"scaler": scaler, "feature_names": feat_cols},
        MODELS_DIR / "logistic_model_meta.pkl",
    )
    print(f"\nSaved model and scaler to {MODELS_DIR}/")

    coef = pd.DataFrame(
        {"feature": feat_cols, "coefficient": model.coef_[0]}
    ).sort_values("coefficient", key=abs, ascending=False)
    coef_path = PROJECT_ROOT / "results" / "tables" / "logistic_regression_coefficients.csv"
    coef_path.parent.mkdir(parents=True, exist_ok=True)
    coef.to_csv(coef_path, index=False)
    print(f"Saved coefficients to {coef_path}")


if __name__ == "__main__":
    main()
