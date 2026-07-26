"""
train_all.py — One command to retrain everything.

Usage: python train_all.py
Prereq: Run data/clean_data.py first to produce cleaned/ CSVs.
"""

import sys
import os

# Add parent to path so imports work
sys.path.insert(0, os.path.dirname(__file__))

from disease_classifier import main as train_disease
from quality_assessor import main as train_milk


def main():
    print("=" * 60)
    print("TRAINING PIPELINE")
    print("=" * 60)

    print("\n── Step 1: Disease Classifier ──")
    train_disease()

    print("\n── Step 2: Milk Yield Model ──")
    train_milk()

    print("\n" + "=" * 60)
    print("All models trained. Artifacts in models/trained_models/")
    print("Evaluation reports in data/cleaned/")
    print("=" * 60)


if __name__ == "__main__":
    main()
