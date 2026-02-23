"""
Hyperparameter tuning for random forest model predicting home_win.
Uses RandomizedSearchCV with time-series aware splits on the training set.
Best model is saved to results/models/ and evaluated on the holdout test season.
"""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "results" / "models"
TABLES_DIR = PROJECT_ROOT / "results" / "tables"

FEATURED_CSV = DATA_DIR / "model_data.csv"
TEST_SEASONS = [2025]

FEATURE_COLS = [
    "home_rolling_avg_wins_10",
    "away_rolling_avg_wins_10",
    "home_rolling_avg_runs_10",
    "away_rolling_avg_runs_10",
    "home_rolling_avg_runs_allowed_10",
    "away_rolling_avg_runs_allowed_10",
    "home_rolling_avg_run_diff_10",
    "away_rolling_avg_run_diff_10",
    "home_rolling_avg_h2h_wins_10",
    "away_rolling_avg_h2h_wins_10",
    "home_rest_days",
    "away_rest_days",
    "home_pitcher_rolling_wins_centered_10",
    "vis_pitcher_rolling_wins_centered_10",
    "vis_b_h_avg10", "home_b_h_avg10",
    "vis_b_hr_avg10", "home_b_hr_avg10",
    "vis_b_w_avg10", "home_b_w_avg10",
    "vis_b_k_avg10", "home_b_k_avg10",
    "vis_b_sb_avg10", "home_b_sb_avg10",
    "vis_obp_avg10", "home_obp_avg10",
    "vis_slg_avg10", "home_slg_avg10",
    "vis_ops_avg10", "home_ops_avg10",
    "vis_era_avg10", "home_era_avg10",
    "vis_whip_avg10", "home_whip_avg10",
    "vis_k9_avg10", "home_k9_avg10",
    "vis_bb9_avg10", "home_bb9_avg10",
    "vis_hr9_avg10", "home_hr9_avg10",
    "vis_d_e_avg10", "home_d_e_avg10",
    "diff_win_avg10", "diff_b_r_avg10", "diff_p_r_avg10", "diff_run_diff_avg10",
    "diff_obp_avg10", "diff_slg_avg10", "diff_ops_avg10",
    "diff_era_avg10", "diff_whip_avg10", "diff_k9_avg10", "diff_bb9_avg10", "diff_hr9_avg10",
    "diff_b_h_avg10", "diff_b_hr_avg10", "diff_b_w_avg10", "diff_b_k_avg10", "diff_b_sb_avg10", "diff_d_e_avg10",
    "daynight", "temp", "windspeed",
]
TARGET_COL = "home_win"

# Hyperparameter search space (focused on reducing overfitting)
PARAM_DISTRIBUTIONS = {
    "n_estimators": [50, 100, 150, 200, 300],
    "max_depth": [3, 5, 7, 10, 12, None],
    "min_samples_split": [2, 5, 10, 20],
    "min_samples_leaf": [1, 2, 4, 8],
    "max_features": ["sqrt", "log2", 0.3, 0.5],
    "class_weight": [None, "balanced"],
}


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
        print("  No test data for holdout seasons; cannot evaluate tuned model.")
        return

    model = RandomForestClassifier(random_state=42)

    cv = TimeSeriesSplit(n_splits=5)
    search = RandomizedSearchCV(
        model,
        param_distributions=PARAM_DISTRIBUTIONS,
        n_iter=50,
        cv=cv,
        scoring="roc_auc",
        random_state=42,
        n_jobs=1,
        verbose=1,
    )

    print("\nRunning hyperparameter search (RandomizedSearchCV, 50 iterations, 5-fold TimeSeriesSplit)...")
    search.fit(X_train, y_train)

    print(f"\nBest CV ROC-AUC: {search.best_score_:.4f}")
    print("Best params:")
    for k, v in search.best_params_.items():
        print(f"  {k}: {v}")

    best_model = search.best_estimator_

    train_pred = best_model.predict(X_train)
    train_prob = best_model.predict_proba(X_train)[:, 1]
    train_acc = accuracy_score(y_train, train_pred)
    train_auc = roc_auc_score(y_train, train_prob)
    print(f"\nTrain set performance:")
    print(f"  Accuracy: {train_acc:.4f}")
    print(f"  ROC-AUC:  {train_auc:.4f}")

    y_pred = best_model.predict(X_test)
    y_prob = best_model.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    print(f"\nTest set performance:")
    print(f"  Accuracy: {acc:.4f}")
    print(f"  ROC-AUC:  {auc:.4f}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, MODELS_DIR / "random_forest_tuned.pkl")
    joblib.dump(
        {"feature_names": feat_cols},
        MODELS_DIR / "random_forest_tuned_meta.pkl",
    )
    print(f"\nSaved tuned model to {MODELS_DIR}/")

    importance = pd.DataFrame(
        {"feature": feat_cols, "importance": best_model.feature_importances_}
    ).sort_values("importance", ascending=False)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    importance.to_csv(TABLES_DIR / "random_forest_tuned_feature_importance.csv", index=False)
    print(f"Saved feature importance to {TABLES_DIR / 'random_forest_tuned_feature_importance.csv'}")

    results_df = pd.DataFrame(search.cv_results_)[
        ["params", "mean_test_score", "std_test_score", "rank_test_score"]
    ].sort_values("rank_test_score")
    results_df.to_csv(TABLES_DIR / "random_forest_tuning_cv_results.csv", index=False)
    print(f"Saved CV results to {TABLES_DIR / 'random_forest_tuning_cv_results.csv'}")


if __name__ == "__main__":
    main()
