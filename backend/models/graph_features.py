"""
graph_features.py — Graph-derived features for the disease classifier.

These features are computed from the SAME relationships stored in Neo4j:

    (Animal)-[:EXHIBITS]->(Symptom)
    (Disease)-[:HAS_SYMPTOM {count}]->(Symptom)

Three families, all derived from graph structure rather than the raw
symptom flags:

  A. Symptom specificity (IDF)
     A symptom present in almost every disease carries little information;
     a symptom seen in only one or two is highly diagnostic. Same idea
     search engines use to know "the" is useless and "cryptosporidiosis"
     is gold.

  B. Symptom co-occurrence
     Some symptoms travel together (Swollen Joints + Lameness). This
     measures how coherent an animal's symptom combination is compared to
     patterns the graph has actually seen.

  C. Novelty / out-of-distribution
     How similar is this symptom set to anything seen before? Used both as
     a model feature and as a signal for the "consult a veterinarian"
     guardrail — "I've never seen this" is a different and better reason to
     defer than "I'm unsure".

── WHY THIS IS AN sklearn TRANSFORMER ──
The graph is built from the training data. Computing these features on all
data and then cross-validating would leak the answer into the features.
Implementing fit/transform means that inside a Pipeline, scikit-learn
refits the extractor on each fold's TRAINING SPLIT ONLY. Leakage safety
becomes structural instead of something we have to remember.
"""

import numpy as np
from itertools import combinations
from sklearn.base import BaseEstimator, TransformerMixin


class GraphFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Input : binary symptom matrix X, shape (n_animals, n_symptoms)
    Output: dense graph-derived feature matrix, shape (n_animals, 7)

    Feature order (see feature_names_):
        0  n_symptoms      how many symptoms observed
        1  max_idf         specificity of the most distinctive symptom
        2  mean_idf        average specificity of the symptom set
        3  mean_cooc       average pairwise co-occurrence strength
        4  min_cooc        weakest pair — flags odd combinations
        5  max_jaccard     similarity to the closest training animal
        6  n_exact_matches training animals with this exact symptom set
    """

    feature_names_ = [
        "n_symptoms",
        "max_idf",
        "mean_idf",
        "mean_cooc",
        "min_cooc",
        "max_jaccard",
        "n_exact_matches",
    ]

    def fit(self, X, y=None):
        X = np.asarray(X)
        n_animals, n_symptoms = X.shape
        self.n_symptoms_in_ = n_symptoms

        # ── A. Symptom specificity (IDF) ──
        # Computed over DISEASES when labels are available (matches the
        # (Disease)-[:HAS_SYMPTOM]->(Symptom) edges in Neo4j); falls back to
        # animal-level document frequency if no labels are supplied.
        if y is not None:
            y = np.asarray(y)
            diseases = np.unique(y)
            n_docs = len(diseases)
            # does disease d ever exhibit symptom s?
            df = np.zeros(n_symptoms)
            for d in diseases:
                present = X[y == d].sum(axis=0) > 0
                df += present.astype(float)
        else:
            n_docs = n_animals
            df = X.sum(axis=0).astype(float)

        # smoothed IDF; +1 keeps it defined for unseen symptoms
        self.idf_ = np.log((1.0 + n_docs) / (1.0 + df)) + 1.0

        # ── B. Co-occurrence matrix ──
        # counts[i, j] = number of training animals exhibiting both i and j
        counts = X.T @ X
        occur = np.diag(counts).astype(float)  # per-symptom totals
        denom = np.minimum.outer(occur, occur)  # normalise by the rarer one
        with np.errstate(divide="ignore", invalid="ignore"):
            self.cooc_ = np.where(denom > 0, counts / denom, 0.0)
        np.fill_diagonal(self.cooc_, 0.0)

        # ── C. Store training symptom sets for novelty comparison ──
        self.train_sets_ = X.astype(bool)
        self.train_sizes_ = self.train_sets_.sum(axis=1)

        return self

    def transform(self, X):
        X = np.asarray(X).astype(bool)
        n_animals = X.shape[0]
        out = np.zeros((n_animals, len(self.feature_names_)))

        for i in range(n_animals):
            present = np.flatnonzero(X[i])
            k = len(present)
            out[i, 0] = k

            if k == 0:
                continue  # leave the rest at zero

            # ── A. IDF aggregates ──
            idfs = self.idf_[present]
            out[i, 1] = idfs.max()
            out[i, 2] = idfs.mean()

            # ── B. Pairwise co-occurrence ──
            if k >= 2:
                pairs = [self.cooc_[a, b] for a, b in combinations(present, 2)]
                out[i, 3] = float(np.mean(pairs))
                out[i, 4] = float(np.min(pairs))
            else:
                # a single symptom has no pairs; treat as fully coherent
                out[i, 3] = 1.0
                out[i, 4] = 1.0

            # ── C. Novelty vs training sets ──
            # NOTE: cast to int before matmul. numpy's `bool @ bool` performs
            # LOGICAL operations and returns booleans, not overlap counts —
            # a silent and very easy bug to ship.
            inter = self.train_sets_.astype(np.int32) @ X[i].astype(np.int32)
            union = self.train_sizes_ + k - inter                # |A ∪ B|
            with np.errstate(divide="ignore", invalid="ignore"):
                jac = np.where(union > 0, inter / union, 0.0)
            out[i, 5] = jac.max() if len(jac) else 0.0
            out[i, 6] = int((jac == 1.0).sum())

        return out

    def get_feature_names_out(self, input_features=None):
        return np.asarray(self.feature_names_, dtype=object)


class SymptomsPlusGraph(BaseEstimator, TransformerMixin):
    """
    Concatenates the original binary symptom vector with the graph features,
    so the model sees both. Standardises the graph block only — the binary
    symptom flags are already on a 0/1 scale.
    """

    def fit(self, X, y=None):
        from sklearn.preprocessing import StandardScaler

        self.graph_ = GraphFeatureExtractor().fit(X, y)
        G = self.graph_.transform(X)
        self.scaler_ = StandardScaler().fit(G)
        return self

    def transform(self, X):
        X = np.asarray(X)
        G = self.scaler_.transform(self.graph_.transform(X))
        return np.hstack([X, G])
