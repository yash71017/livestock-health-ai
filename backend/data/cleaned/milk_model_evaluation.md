# Milk Yield Model — Evaluation Report

**Note:** This model predicts daily milk yield (L/day) from breed, age, and weight.
It does NOT assess milk quality — no biochemical data exists in the training set.

## Baseline (predict mean=12.0 L/day)
MAE: 3.64

## Random Forest (100 trees, max_depth=6)
CV MAE: 3.80 L/day

## Gradient Boosting (100 trees, max_depth=4)
CV MAE: 4.29 L/day

## Final Model: RandomForest
Full-data MAE: 1.97
Full-data RMSE: 2.37
Full-data R²: 0.670
Trained on 68 samples

## Feature Importances
  Weight: 0.4417
  breed_encoded: 0.3148
  Age: 0.2435
