"""
quality_assessor.py — Milk yield prediction model.

HONEST NOTE: The original project claimed to assess milk quality via
biochemical parameters (fat, protein, pH, SCC, bacteria). The actual data
contains NONE of those — only herd management metrics and daily yield.

This model now honestly predicts MILK YIELD (L/day) from animal attributes
(breed, age, weight), which IS supported by the data.

The UI will be renamed from "Milk Quality Analyser" to "Milk Yield Estimator".
"""

import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.dummy import DummyRegressor
from sklearn.preprocessing import LabelEncoder

SEED = 42
np.random.seed(SEED)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "trained_models")


def load_data():
    milk = pd.read_csv(os.path.join(DATA_DIR, "cleaned_milk.csv"))
    return milk


def prepare_features(df):
    """Encode breed as numeric, use age + weight as features."""
    le = LabelEncoder()
    df = df.copy()
    df["breed_encoded"] = le.fit_transform(df["Breed"])

    feature_cols = ["breed_encoded", "Age", "Weight"]
    X = df[feature_cols].values
    y = df["Milk_Yield(L/day)"].values

    return X, y, feature_cols, le


def train_and_evaluate(X, y, feature_cols):
    """Train with cross-validation, return best model and report."""
    reports = []
    cv = KFold(n_splits=min(5, len(X)), shuffle=True, random_state=SEED)

    # ── Baseline: predict mean ──
    dummy = DummyRegressor(strategy="mean")
    dummy_scores = cross_val_score(dummy, X, y, cv=cv, scoring="neg_mean_absolute_error")
    baseline_mae = -dummy_scores.mean()
    reports.append(f"## Baseline (predict mean={np.mean(y):.1f} L/day)")
    reports.append(f"MAE: {baseline_mae:.2f}")
    reports.append("")

    # ── Random Forest ──
    rf = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=SEED)
    rf_mae_scores = cross_val_score(rf, X, y, cv=cv, scoring="neg_mean_absolute_error")
    rf_mae = -rf_mae_scores.mean()

    # ── Gradient Boosting ──
    gb = GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=SEED)
    gb_mae_scores = cross_val_score(gb, X, y, cv=cv, scoring="neg_mean_absolute_error")
    gb_mae = -gb_mae_scores.mean()

    reports.append(f"## Random Forest (100 trees, max_depth=6)")
    reports.append(f"CV MAE: {rf_mae:.2f} L/day")
    reports.append("")

    reports.append(f"## Gradient Boosting (100 trees, max_depth=4)")
    reports.append(f"CV MAE: {gb_mae:.2f} L/day")
    reports.append("")

    # Pick best
    if gb_mae < rf_mae:
        best = gb
        best_name = "GradientBoosting"
        best_mae = gb_mae
    else:
        best = rf
        best_name = "RandomForest"
        best_mae = rf_mae

    print(f"  Best: {best_name} (MAE={best_mae:.2f} vs baseline={baseline_mae:.2f})")

    # Train final on all data
    best.fit(X, y)

    # Full-data metrics
    y_pred = best.predict(X)
    full_mae = mean_absolute_error(y, y_pred)
    full_rmse = np.sqrt(mean_squared_error(y, y_pred))
    full_r2 = r2_score(y, y_pred)

    reports.append(f"## Final Model: {best_name}")
    reports.append(f"Full-data MAE: {full_mae:.2f}")
    reports.append(f"Full-data RMSE: {full_rmse:.2f}")
    reports.append(f"Full-data R²: {full_r2:.3f}")
    reports.append(f"Trained on {len(X)} samples")
    reports.append("")

    # Feature importances
    reports.append("## Feature Importances")
    if hasattr(best, "feature_importances_"):
        for name, imp in sorted(
            zip(feature_cols, best.feature_importances_), key=lambda x: -x[1]
        ):
            reports.append(f"  {name}: {imp:.4f}")
    reports.append("")

    return best, "\n".join(reports), best_name


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    print("Loading milk data...")
    df = load_data()
    print(f"  {len(df)} records")

    if len(df) < 10:
        print("  WARNING: Very few milk records. Model will be unreliable.")

    print("Preparing features...")
    X, y, feature_cols, breed_encoder = prepare_features(df)

    print("Training and evaluating...")
    model, eval_report, model_name = train_and_evaluate(X, y, feature_cols)

    # Save
    artifact = {
        "model": model,
        "model_name": model_name,
        "feature_cols": feature_cols,
        "breed_encoder": breed_encoder,
        "breeds_known": list(breed_encoder.classes_),
        "yield_range": {"min": float(np.min(y)), "max": float(np.max(y)), "mean": float(np.mean(y))},
    }

    path = os.path.join(MODEL_DIR, "milk_model.pkl")
    joblib.dump(artifact, path)
    print(f"  Saved to {path}")

    report_path = os.path.join(DATA_DIR, "milk_model_evaluation.md")
    header = "# Milk Yield Model — Evaluation Report\n\n"
    header += "**Note:** This model predicts daily milk yield (L/day) from breed, age, and weight.\n"
    header += "It does NOT assess milk quality — no biochemical data exists in the training set.\n\n"
    with open(report_path, "w") as f:
        f.write(header + eval_report)
    print(f"  Evaluation report: {report_path}")


if __name__ == "__main__":
    main()
