# Graph Features — Experiment Report

**Question:** the project stores its data in a knowledge graph. Can graph-derived
features improve disease prediction, or is Neo4j just storage with extra steps?

**Answer:** they cannot — and the reason turns out to be the most useful thing
this project has established about its own data.

---

## 1. What was built

Three families of features, computed from the same relationships stored in Neo4j
(`(Animal)-[:EXHIBITS]->(Symptom)`, `(Disease)-[:HAS_SYMPTOM]->(Symptom)`):

| Feature | Idea |
|---|---|
| `max_idf`, `mean_idf` | **Symptom specificity.** A symptom present in nearly every disease carries little information; a rare one is diagnostic. Same principle that makes "the" useless and "cryptosporidiosis" valuable to a search engine. |
| `mean_cooc`, `min_cooc` | **Co-occurrence coherence.** Some symptoms travel together. This measures how well an animal's combination matches patterns the graph has actually seen. |
| `max_jaccard`, `n_exact_matches` | **Novelty.** How similar is this symptom set to anything in the reference data? |
| `n_symptoms` | Count of observed symptoms. |

### Leakage safety

The graph is derived from the training data, so computing these features over the
full dataset and then cross-validating would leak the answer into the features.

`GraphFeatureExtractor` is implemented as a scikit-learn transformer with
`fit`/`transform`. Inside a `Pipeline`, scikit-learn refits it on **each fold's
training split only**. Leakage safety is structural rather than a rule someone has
to remember.

---

## 2. Results

5-fold stratified cross-validation, seed 42, 146 animals, 15 symptoms, 15 classes.

| Model | Accuracy | Macro F1 |
|---|---|---|
| Majority class (naive baseline) | 0.137 | 0.016 |
| **Logistic Regression — symptoms only** | **0.240** | **0.225** |
| Logistic Regression — symptoms + graph | 0.192 | 0.171 |
| Logistic Regression — graph features only | 0.158 | 0.106 |
| Random Forest — symptoms only | 0.205 | 0.201 |
| Random Forest — symptoms + graph | 0.205 | 0.191 |

**Graph features reduced accuracy by 4.8 points.** Adding seven weakly-informative
columns to a 15-feature model trained on 146 samples dilutes the signal — ordinary
small-data behaviour.

The features were **not** shipped into the model. Keeping them because they sound
impressive would have been dishonest.

---

## 3. Why they could never have helped

Investigating the failure produced a more important result.

### The Bayes ceiling is 40.4%

The best accuracy **any** model can reach on this data — regardless of algorithm,
tuning, or features — is **40.4%**, because the inputs do not determine the labels.

Only **12 of 27** distinct symptom combinations map to a single disease. The
remaining 15 are ambiguous, covering **90.4%** of all animals.

The clearest case — `Coughing + Fever + Lethargy + Loss of Appetite` — occurs 57
times with **13 different labels**:

| Disease | Cases |
|---|---|
| Bovine Respiratory Disease | 11 |
| Bovine Tuberculosis | 10 |
| Bluetongue | 8 |
| Scrapie | 8 |
| Foot and Mouth Disease | 5 |
| *…and 8 more* | |

Identical inputs, thirteen different answers. No model can separate them.

### Where the current model actually sits

```
13.7%          24.0%                40.4%                        100%
  │              │                    │                            │
  ▼              ▼                    ▼                            ▼
naive         current              CEILING                      perfect
baseline       model            (irreducible)
              └──── captures ~59% of achievable signal ────┘
```

**24% accuracy against a 40% ceiling** is a materially different claim from
"24% accuracy". The model is capturing most of the signal that exists.

### The general principle

The graph's disease–symptom edges were *derived from* the same symptom–disease
pairs the model already sees. Features computed from them reorganise that
information; they cannot create more of it.

**You cannot extract signal that is not there.** The bottleneck is the data, not
the model or the feature engineering.

---

## 4. A bug worth recording

An early version of the novelty feature used `bool_array @ bool_array` in NumPy.
That performs **logical** operations and returns booleans — not overlap counts. The
feature silently produced nonsense (every animal appeared equally novel;
`n_exact_matches` was always zero).

It was caught by inspecting the feature distributions — `max_jaccard` had a
standard deviation of 0.005, which is implausible for a real similarity measure —
rather than by any error message. Fixed by casting to `int32` before the matmul.

Lesson: look at the distribution of every engineered feature before trusting it.

---

## 5. What was shipped instead

Although graph features do not improve accuracy, the graph still does real work at
inference time — as **explanation** rather than prediction.

`/api/diagnose` now runs a live Cypher query:

```cypher
MATCH (a:Animal)-[:PREDICTED_WITH]->(d:Disease)
WITH a, d, [(a)-[:EXHIBITS]->(s:Symptom) | s.name] AS syms
WHERE all(x IN $symptoms WHERE x IN syms)
RETURN d.name AS disease, count(DISTINCT a) AS cases
ORDER BY cases DESC
```

and returns one of three verdicts:

| Mode | Meaning shown to the user |
|---|---|
| `distinctive` | The symptoms point at a single disease in the graph. |
| `ambiguous` | *"These symptoms match 13 diseases across 57 animals — symptoms alone cannot separate them."* |
| `unseen` | The combination appears nowhere in the reference data; the prediction is extrapolating. |

This changes the guardrail from a restatement of the score into an actual reason:

- Before: *"Confidence 17.6% — consult a veterinarian."*
- After: *"These symptoms match 13 diseases in the knowledge graph. Symptoms alone
  cannot separate them — veterinary examination is needed."*

Measured as a deferral signal, graph ambiguity does **not** outperform confidence
(31.8% vs 33.0% accuracy on the retained cases), so it was not used to *make* the
decision — only to explain it. The graph is queried live and shapes what the user
is told; it is no longer only storage.

---

## 6. Honest summary

- Graph-derived model features: **tried, measured, rejected** — they reduced accuracy.
- The project's central "graph-AI" framing is therefore stated accurately: the graph
  provides storage, relationship context, and **explanation of uncertainty**, not
  predictive signal.
- The binding constraint is the dataset: synthetic, 146 rows, and ambiguous by
  construction. Better features cannot fix it; only better data can.

## Reproducing

```bash
cd backend
python models/evaluate_graph_features.py
```
