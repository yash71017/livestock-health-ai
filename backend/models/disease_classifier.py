"""
disease_classifier.py — Train disease prediction model from cleaned data.

Uses actual symptom-disease relationships from the dataset.
Groups rare diseases (<4 samples) into "Rare — Consult Veterinarian".
Evaluates with stratified cross-validation and per-class metrics.
"""

import pandas as pd
import numpy as np
import json
import os
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier

SEED = 42
np.random.seed(SEED)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "trained_models")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")

MIN_SAMPLES_PER_CLASS = 4
RARE_LABEL = "Rare — Consult Veterinarian"


def load_data():
    df = pd.read_csv(os.path.join(DATA_DIR, "ml_training_data.csv"))
    vocab = json.load(open(os.path.join(DATA_DIR, "vocab.json")))
    return df, vocab


def prepare_features(df, vocab):
    """Extract symptom feature columns and disease labels."""
    symptom_cols = [c for c in df.columns if c.startswith("sym_")]
    X = df[symptom_cols].values
    y = df["Disease"].values
    feature_names = [c.replace("sym_", "") for c in symptom_cols]
    return X, y, feature_names, symptom_cols


def group_rare_diseases(y, min_samples=MIN_SAMPLES_PER_CLASS):
    """Group diseases with fewer than min_samples into RARE_LABEL."""
    from collections import Counter
    counts = Counter(y)
    mapping = {}
    for disease, count in counts.items():
        if count < min_samples:
            mapping[disease] = RARE_LABEL
        else:
            mapping[disease] = disease
    y_grouped = np.array([mapping[d] for d in y])
    print(f"  Grouped {sum(1 for d,c in counts.items() if c < min_samples)} rare diseases → '{RARE_LABEL}'")
    print(f"  Final classes: {len(set(y_grouped))}")
    return y_grouped, mapping


def train_and_evaluate(X, y, feature_names):
    """Train with cross-validation, evaluate, return best model."""
    reports = []

    # ── Baseline: majority class ──
    dummy = DummyClassifier(strategy="most_frequent", random_state=SEED)
    dummy.fit(X, y)
    y_pred_dummy = cross_val_predict(dummy, X, y, cv=min(5, min(pd.Series(y).value_counts())))
    baseline_acc = accuracy_score(y, y_pred_dummy)
    reports.append(f"## Baseline (majority class)")
    reports.append(f"Accuracy: {baseline_acc:.3f}")
    reports.append("")

    # ── Logistic Regression (interpretable) ──
    cv = StratifiedKFold(n_splits=min(5, min(pd.Series(y).value_counts())), shuffle=True, random_state=SEED)

    lr = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=SEED,
        solver="lbfgs",
        C=1.0,
    )
    y_pred_lr = cross_val_predict(lr, X, y, cv=cv)
    lr_acc = accuracy_score(y, y_pred_lr)
    lr_report = classification_report(y, y_pred_lr, zero_division=0)

    reports.append("## Logistic Regression (class_weight=balanced)")
    reports.append(f"Accuracy: {lr_acc:.3f}")
    reports.append(f"Classification Report:\n{lr_report}")
    reports.append("")

    # ── Gradient Boosting ──
    gb = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=4,
        random_state=SEED,
    )
    y_pred_gb = cross_val_predict(gb, X, y, cv=cv)
    gb_acc = accuracy_score(y, y_pred_gb)
    gb_report = classification_report(y, y_pred_gb, zero_division=0)

    reports.append("## Gradient Boosting")
    reports.append(f"Accuracy: {gb_acc:.3f}")
    reports.append(f"Classification Report:\n{gb_report}")
    reports.append("")

    # ── Pick best model ──
    if gb_acc > lr_acc + 0.02:
        print(f"  Picking Gradient Boosting (acc={gb_acc:.3f} vs LR={lr_acc:.3f})")
        best_model = gb
        best_name = "GradientBoosting"
    else:
        print(f"  Picking Logistic Regression for interpretability (acc={lr_acc:.3f} vs GB={gb_acc:.3f})")
        best_model = lr
        best_name = "LogisticRegression"

    # ── Train final model on all data with calibration ──
    best_model.fit(X, y)
    calibrated = CalibratedClassifierCV(best_model, cv=cv, method="sigmoid")
    calibrated.fit(X, y)

    reports.append(f"## Final Model: {best_name} (calibrated)")
    reports.append(f"Trained on {len(X)} samples, {len(set(y))} classes")
    reports.append("")

    # ── Feature importances ──
    reports.append("## Feature Importances (symptom influence)")
    if best_name == "LogisticRegression":
        # For multiclass LR, average absolute coefficient across classes
        importances = np.mean(np.abs(best_model.coef_), axis=0)
    else:
        importances = best_model.feature_importances_
    ranked = sorted(zip(feature_names, importances), key=lambda x: -x[1])
    for name, imp in ranked:
        reports.append(f"  {name}: {imp:.4f}")
    reports.append("")

    return calibrated, best_model, "\n".join(reports), best_name


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    print("Loading cleaned data...")
    df, vocab = load_data()

    print("Preparing features...")
    X, y_raw, feature_names, symptom_cols = prepare_features(df, vocab)
    print(f"  {X.shape[0]} samples, {X.shape[1]} symptom features")

    print("Grouping rare diseases...")
    y, disease_mapping = group_rare_diseases(y_raw)

    print("Training and evaluating...")
    calibrated_model, raw_model, eval_report, model_name = train_and_evaluate(
        X, y, feature_names
    )

    # ── Save ──
    artifact = {
        "model": calibrated_model,
        "raw_model": raw_model,
        "model_name": model_name,
        "feature_names": feature_names,
        "symptom_columns": symptom_cols,
        "classes": list(calibrated_model.classes_),
        "disease_mapping": disease_mapping,
        "vocab_symptoms": vocab["symptoms"],
        "min_confidence_threshold": 0.25,
    }

    path = os.path.join(MODEL_DIR, "disease_model.pkl")
    joblib.dump(artifact, path)
    print(f"  Saved to {path}")

    # ── Save evaluation report ──
    report_path = os.path.join(REPORT_DIR, "disease_model_evaluation.md")
    header = "# Disease Classification Model — Evaluation Report\n\n"
    with open(report_path, "w") as f:
        f.write(header + eval_report)
    print(f"  Evaluation report: {report_path}")

    return artifact


if __name__ == "__main__":
    main()
