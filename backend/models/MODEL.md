# MODEL.md — Model Card

## Disease Classifier

| Item | Value |
|------|-------|
| Algorithm | Logistic Regression (calibrated via CalibratedClassifierCV) |
| Input | 15-dimensional binary symptom vector |
| Output | Disease class + calibrated probability |
| Classes | 15 (14 diseases + "Rare — Consult Veterinarian") |
| Training samples | 146 |
| Cross-validated accuracy | **24%** (vs 14% majority-class baseline) |
| Chosen over | GradientBoosting (25% accuracy — marginal gain not worth interpretability loss) |

### Per-Class Performance (highlights)

| Disease | Precision | Recall | F1 | Support |
|---------|-----------|--------|-----|---------|
| Caprine Arthritis Encephalitis | 0.56 | 0.53 | 0.55 | 17 |
| Coccidiosis | 0.40 | 1.00 | 0.57 | 4 |
| Mastitis | 0.57 | 0.57 | 0.57 | 7 |
| Caprine Pleuropneumonia | 0.42 | 1.00 | 0.59 | 5 |
| Bovine Respiratory Disease | 0.00 | 0.00 | 0.00 | 17 |

Some diseases (BRD, Foot and Mouth) get 0% recall — the model cannot distinguish them from others with similar symptom profiles given only 15 binary features.

### Top Symptom Influences

1. Vomiting (0.74)
2. Coughing (0.63)
3. Loss of Appetite (0.57)
4. Fever (0.50)
5. Decreased Milk Yield (0.48)

### Guardrails

- If top prediction confidence < 25%, the API returns "Uncertain — Consult Veterinarian"
- Unrecognised symptoms are flagged in the response as `unmatchedSymptoms`

---

## Milk Yield Regressor

| Item | Value |
|------|-------|
| Algorithm | RandomForestRegressor (100 trees, max_depth=6) |
| Input | breed (encoded), age, weight |
| Output | Estimated daily milk yield (L/day) |
| Training samples | 68 |
| Cross-validated MAE | **3.80 L/day** (vs 3.64 baseline — barely beats predicting the mean) |
| Full-data R² | 0.669 |

### Honest Assessment

The milk model barely outperforms predicting the mean (12 L/day for all animals). With only 68 samples and 3 features, this is expected. It's included for completeness but should be clearly labelled as approximate.

### Feature Importances

1. Weight (0.44)
2. Breed (0.31)
3. Age (0.24)

---

## Intended Use

**Decision support only.** These models are trained on synthetic data and are not validated for clinical use. They demonstrate the architecture and approach of a graph-backed veterinary AI system.

## What These Models Are NOT

- Not a substitute for veterinary diagnosis
- Not trained on real clinical data
- Not validated against known disease outcomes
- Not suitable for any production deployment without real data and clinical validation
