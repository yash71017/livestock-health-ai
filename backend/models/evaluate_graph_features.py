"""
evaluate_graph_features.py — Does the graph actually help?

Compares, under identical leakage-safe cross-validation:

    1. Baseline        : binary symptom vector only  (the current model)
    2. Graph-augmented : symptom vector + graph-derived features

Both run through a Pipeline, so the graph feature extractor is refitted on
each fold's training split. No information from the held-out fold reaches
the features.

Run: python models/evaluate_graph_features.py
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from collections import Counter

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.dummy import DummyClassifier

sys.path.insert(0, os.path.dirname(__file__))
from graph_features import SymptomsPlusGraph, GraphFeatureExtractor

SEED = 42
np.random.seed(SEED)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
MIN_SAMPLES_PER_CLASS = 4
RARE_LABEL = "Rare — Consult Veterinarian"


def load():
    df = pd.read_csv(os.path.join(DATA_DIR, "ml_training_data.csv"))
    sym_cols = [c for c in df.columns if c.startswith("sym_")]
    X = df[sym_cols].values.astype(float)
    y_raw = df["Disease"].values
    names = [c.replace("sym_", "") for c in sym_cols]

    counts = Counter(y_raw)
    y = np.array([d if counts[d] >= MIN_SAMPLES_PER_CLASS else RARE_LABEL for d in y_raw])
    return X, y, names


def evaluate(name, pipeline, X, y, cv):
    pred = cross_val_predict(pipeline, X, y, cv=cv)
    return {
        "name": name,
        "accuracy": accuracy_score(y, pred),
        "macro_f1": f1_score(y, pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y, pred, average="weighted", zero_division=0),
        "pred": pred,
    }


def main():
    X, y, names = load()
    n_folds = min(5, min(Counter(y).values()))
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=SEED)

    print("=" * 66)
    print("GRAPH FEATURE EVALUATION")
    print("=" * 66)
    print(f"{X.shape[0]} animals · {X.shape[1]} symptoms · {len(set(y))} classes")
    print(f"{n_folds}-fold stratified cross-validation, seed={SEED}")
    print()

    results = []

    # ── 0. Naive baseline ──
    results.append(evaluate(
        "Majority class (naive baseline)",
        Pipeline([("clf", DummyClassifier(strategy="most_frequent"))]),
        X, y, cv))

    # ── 1. Current model: symptoms only ──
    results.append(evaluate(
        "Logistic Regression — symptoms only  [CURRENT]",
        Pipeline([("clf", LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=SEED))]),
        X, y, cv))

    # ── 2. Graph-augmented ──
    results.append(evaluate(
        "Logistic Regression — symptoms + GRAPH",
        Pipeline([
            ("feat", SymptomsPlusGraph()),
            ("clf", LogisticRegression(
                max_iter=2000, class_weight="balanced", random_state=SEED)),
        ]),
        X, y, cv))

    # ── 3. Graph features ALONE (are they informative at all?) ──
    results.append(evaluate(
        "Logistic Regression — GRAPH features only",
        Pipeline([
            ("feat", GraphFeatureExtractor()),
            ("clf", LogisticRegression(
                max_iter=2000, class_weight="balanced", random_state=SEED)),
        ]),
        X, y, cv))

    # ── 4. Tree model, which can use non-linear graph features better ──
    results.append(evaluate(
        "Random Forest — symptoms only",
        Pipeline([("clf", RandomForestClassifier(
            n_estimators=300, class_weight="balanced", random_state=SEED))]),
        X, y, cv))

    results.append(evaluate(
        "Random Forest — symptoms + GRAPH",
        Pipeline([
            ("feat", SymptomsPlusGraph()),
            ("clf", RandomForestClassifier(
                n_estimators=300, class_weight="balanced", random_state=SEED)),
        ]),
        X, y, cv))

    # ── Report ──
    print(f"{'Model':<48}{'Acc':>7}{'MacroF1':>10}{'WtdF1':>9}")
    print("-" * 74)
    for r in results:
        print(f"{r['name']:<48}{r['accuracy']:>7.3f}{r['macro_f1']:>10.3f}{r['weighted_f1']:>9.3f}")
    print()

    base = results[1]
    graph = results[2]
    d_acc = graph["accuracy"] - base["accuracy"]
    d_f1 = graph["macro_f1"] - base["macro_f1"]

    print("VERDICT (Logistic Regression, symptoms vs symptoms+graph)")
    print(f"  accuracy : {base['accuracy']:.3f} -> {graph['accuracy']:+.3f} ... {d_acc:+.3f}")
    print(f"  macro F1 : {base['macro_f1']:.3f} -> {graph['macro_f1']:.3f} ... {d_f1:+.3f}")
    print()

    rf_base, rf_graph = results[4], results[5]
    print("VERDICT (Random Forest, symptoms vs symptoms+graph)")
    print(f"  accuracy : {rf_base['accuracy']:.3f} -> {rf_graph['accuracy']:.3f} "
          f"... {rf_graph['accuracy']-rf_base['accuracy']:+.3f}")
    print(f"  macro F1 : {rf_base['macro_f1']:.3f} -> {rf_graph['macro_f1']:.3f} "
          f"... {rf_graph['macro_f1']-rf_base['macro_f1']:+.3f}")
    print()

    # ── What the graph features look like ──
    ex = GraphFeatureExtractor().fit(X, y)
    G = ex.transform(X)
    print("GRAPH FEATURE SUMMARY (fitted on all data, for inspection only)")
    print(f"{'feature':<18}{'mean':>9}{'std':>9}{'min':>9}{'max':>9}")
    print("-" * 54)
    for i, fname in enumerate(ex.feature_names_):
        print(f"{fname:<18}{G[:,i].mean():>9.3f}{G[:,i].std():>9.3f}"
              f"{G[:,i].min():>9.3f}{G[:,i].max():>9.3f}")
    print()

    print("MOST / LEAST DISTINCTIVE SYMPTOMS (IDF)")
    order = np.argsort(-ex.idf_)
    for i in order[:3]:
        print(f"  most  {names[i]:<28}{ex.idf_[i]:.3f}")
    for i in order[-3:]:
        print(f"  least {names[i]:<28}{ex.idf_[i]:.3f}")

    return results


if __name__ == "__main__":
    main()
