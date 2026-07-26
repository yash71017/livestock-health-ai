# DATA.md — Dataset Card

## Overview

| Item | Value |
|------|-------|
| Total raw records | 431 animals |
| After livestock filter | 146 animals (Cow: 68, Goat: 39, Sheep: 39) |
| Disease classes | 30 (after standardisation from 139 raw labels) |
| Symptom vocabulary | 15 standardised symptoms |
| Milk yield records | 68 |
| Data origin | **Synthetic** — appears machine-generated, not from real clinical records |

## Sources

All data files were provided as part of an academic project. The original source appears to be a synthetically generated dataset, likely adapted from patterns found in Kaggle veterinary datasets. No real animal health records, farm data, or clinical trial data are included.

**No milk biochemistry data exists.** The MilkData file (1000 rows) contains herd management metrics (yield, feed type, body temperature, heart rate) but none of the biochemical parameters (fat %, protein %, pH, somatic cell count, bacteria count) that the original project design assumed.

## Transformations (clean_data.py)

1. **Scope filter:** Kept only livestock species (Cow, Goat, Sheep). Dropped Dogs (75), Cats (72), Horses (66), Pigs (38), Rabbits (34).
2. **Disease standardisation:** Merged duplicate disease names. Examples:
   - "Blue Tongue" / "Blue Tongue Disease" / "Blue Tongue Virus" / "Bluetongue Virus" → **Bluetongue**
   - "Foot and Mouth Disease" / "Foot-and-Mouth Disease" → **Foot and Mouth Disease**
   - "Bovine Mastitis" / "Mastitis" → **Mastitis**
   - Full mapping in `clean_data.py::DISEASE_CANONICAL`
3. **Symptom standardisation:**
   - "Appetite Loss" / "Reduced Appetite" / "Loss of Appetite" → **Loss of Appetite**
   - "Reduced Milk Yield" / "Reduced Milk Production" → **Decreased Milk Yield**
   - "No" (used as a symptom placeholder) → treated as missing
4. **ID unification:** Animal IDs normalised to "A1"…"A431" format.
5. **Validation:** Age [0–25 years], Weight [5–1500 kg]. No violations found.

## Class Distribution (Disease)

Top 10 (of 30):

| Disease | Samples |
|---------|---------|
| Bovine Respiratory Disease | 17 |
| Caprine Arthritis Encephalitis | 17 |
| Bovine Tuberculosis | 16 |
| Scrapie | 12 |
| Bluetongue | 11 |
| Foot and Mouth Disease | 10 |
| Johne's Disease | 9 |
| Mastitis | 7 |
| Pneumonia | 6 |
| Caprine Pleuropneumonia | 5 |

16 diseases have ≤2 samples and are grouped as "Rare — Consult Veterinarian" for ML purposes.

## Known Limitations

- **Synthetic data.** Predictions trained on this data are not clinically meaningful.
- **No Buffalo data** despite being in the project scope.
- **Severe class imbalance:** 16 diseases have ≤2 samples.
- **Limited symptom vocabulary:** Only 15 symptoms across 30 diseases is unrealistically sparse for real diagnosis.
- **No temporal dimension:** All records are cross-sectional snapshots, not time-series.

## What This Data Should NOT Be Used For

- Real veterinary diagnosis or treatment decisions.
- Claims about disease prevalence or symptom-disease relationships in actual livestock populations.
- Training a model intended for deployment in a real farming or veterinary context.
