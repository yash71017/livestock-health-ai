"""
routes.py — Flask API endpoints.

Schema (Neo4j):
    (:Animal {animalId, animalType, breed, age, gender, weight})
    (:Disease {name})
    (:Symptom {name})
    (:MilkRecord {animalId, breed, age, weight, milkYield})
    (Animal)-[:EXHIBITS]->(Symptom)
    (Animal)-[:PREDICTED_WITH]->(Disease)
    (Animal)-[:HAS_MILK_RECORD]->(MilkRecord)
    (Disease)-[:HAS_SYMPTOM]->(Symptom)
"""

from flask import Blueprint, request, jsonify
import joblib
import numpy as np
import os
import json
import traceback

api_bp = Blueprint("api", __name__, url_prefix="/api")

# ── Load ML models at import time ──
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "trained_models")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")

disease_artifact = None
milk_artifact = None
vocab = None

def load_models():
    global disease_artifact, milk_artifact, vocab
    try:
        disease_artifact = joblib.load(os.path.join(MODEL_DIR, "disease_model.pkl"))
        print(f"Loaded disease model: {disease_artifact['model_name']}, "
              f"{len(disease_artifact['classes'])} classes")
    except Exception as e:
        print(f"WARNING: Could not load disease model: {e}")

    try:
        milk_artifact = joblib.load(os.path.join(MODEL_DIR, "milk_model.pkl"))
        print(f"Loaded milk model: {milk_artifact['model_name']}")
    except Exception as e:
        print(f"WARNING: Could not load milk model: {e}")

    try:
        with open(os.path.join(DATA_DIR, "vocab.json")) as f:
            vocab = json.load(f)
        print(f"Loaded vocab: {len(vocab['symptoms'])} symptoms, {len(vocab['diseases'])} diseases")
    except Exception as e:
        print(f"WARNING: Could not load vocab: {e}")


# ── Helper ──
def get_db():
    """Get the Neo4j query runner. Imported here to avoid circular imports."""
    from database.neo4j_connector import run_query, run_write
    return run_query, run_write


# ═══════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════
@api_bp.route("/stats", methods=["GET"])
def get_stats():
    """Dashboard statistics — live from Neo4j."""
    try:
        run_query, _ = get_db()

        animal_count = run_query("MATCH (a:Animal) RETURN count(a) AS count")[0]["count"]
        disease_count = run_query("MATCH (d:Disease) RETURN count(d) AS count")[0]["count"]
        symptom_count = run_query("MATCH (s:Symptom) RETURN count(s) AS count")[0]["count"]
        milk_count = run_query("MATCH (m:MilkRecord) RETURN count(m) AS count")[0]["count"]

        # Average milk yield
        avg_yield_result = run_query(
            "MATCH (m:MilkRecord) RETURN avg(m.milkYield) AS avg"
        )
        avg_yield = round(avg_yield_result[0]["avg"] or 0, 1)

        # Animal types breakdown
        type_counts = run_query(
            "MATCH (a:Animal) RETURN a.animalType AS type, count(a) AS count "
            "ORDER BY count DESC"
        )

        return jsonify({
            "totalAnimals": animal_count,
            "totalDiseases": disease_count,
            "totalSymptoms": symptom_count,
            "milkRecords": milk_count,
            "avgMilkYield": avg_yield,
            "animalTypes": [{"type": r["type"], "count": r["count"]} for r in type_counts],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# ANIMALS
# ═══════════════════════════════════════════════════════════════
@api_bp.route("/animals", methods=["GET"])
def get_animals():
    """List all animals with optional type filter."""
    try:
        run_query, _ = get_db()
        animal_type = request.args.get("type")

        if animal_type:
            results = run_query(
                "MATCH (a:Animal) WHERE a.animalType = $type "
                "RETURN a.animalId AS id, a.animalType AS type, a.breed AS breed, "
                "a.age AS age, a.gender AS gender, a.weight AS weight "
                "ORDER BY a.animalId",
                {"type": animal_type}
            )
        else:
            results = run_query(
                "MATCH (a:Animal) "
                "RETURN a.animalId AS id, a.animalType AS type, a.breed AS breed, "
                "a.age AS age, a.gender AS gender, a.weight AS weight "
                "ORDER BY a.animalId"
            )

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/animals/<animal_id>", methods=["GET"])
def get_animal(animal_id):
    """Get one animal with its symptoms and disease."""
    try:
        run_query, _ = get_db()

        result = run_query(
            "MATCH (a:Animal {animalId: $id}) "
            "OPTIONAL MATCH (a)-[:EXHIBITS]->(s:Symptom) "
            "OPTIONAL MATCH (a)-[:PREDICTED_WITH]->(d:Disease) "
            "OPTIONAL MATCH (a)-[:HAS_MILK_RECORD]->(m:MilkRecord) "
            "RETURN a.animalId AS id, a.animalType AS type, a.breed AS breed, "
            "a.age AS age, a.gender AS gender, a.weight AS weight, "
            "collect(DISTINCT s.name) AS symptoms, "
            "collect(DISTINCT d.name) AS diseases, "
            "m.milkYield AS milkYield",
            {"id": animal_id}
        )

        if not result or result[0]["id"] is None:
            return jsonify({"error": "Animal not found"}), 404

        return jsonify(result[0])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# DIAGNOSIS (ML prediction)
# ═══════════════════════════════════════════════════════════════
@api_bp.route("/diagnose", methods=["POST"])
def diagnose():
    """
    Predict disease from symptoms.
    
    Body: { "animalId": "A5" (optional), "symptoms": ["Fever", "Coughing"] }
    Returns: { "disease", "confidence", "allPredictions", "drivingSymptoms",
               "disclaimer" }
    """
    try:
        if disease_artifact is None:
            return jsonify({"error": "Disease model not loaded"}), 503

        data = request.get_json()
        symptoms = data.get("symptoms", [])

        if not symptoms:
            return jsonify({"error": "No symptoms provided"}), 400

        # Build feature vector: binary for each known symptom
        known_symptoms = disease_artifact["vocab_symptoms"]
        feature_vec = np.zeros(len(known_symptoms))
        matched = []
        unmatched = []

        for s in symptoms:
            if s in known_symptoms:
                feature_vec[known_symptoms.index(s)] = 1
                matched.append(s)
            else:
                unmatched.append(s)

        if not matched:
            return jsonify({
                "disease": "Unknown",
                "confidence": 0,
                "message": "None of the provided symptoms match the model's vocabulary.",
                "unmatchedSymptoms": unmatched,
                "disclaimer": "This is decision support only, not a veterinary diagnosis."
            })

        # Predict
        model = disease_artifact["model"]
        probs = model.predict_proba(feature_vec.reshape(1, -1))[0]
        classes = disease_artifact["classes"]

        # Sort by probability
        ranked = sorted(zip(classes, probs), key=lambda x: -x[1])
        top_disease, top_conf = ranked[0]

        # These are internal guardrail buckets, not real diseases. They should
        # never appear in the ranked list a user reads.
        GUARDRAIL_LABELS = {"Uncertain — Consult Veterinarian", "Rare — Consult Veterinarian"}

        # Low-confidence guardrail
        confidence_threshold = disease_artifact.get("min_confidence_threshold", 0.25)
        if top_conf < confidence_threshold:
            top_disease = "Uncertain — Consult Veterinarian"

        # Feature importance: which symptoms drove this prediction
        driving = [s for s in matched]  # All matched symptoms contributed

        # Get treatment/info from graph if possible
        treatments = []
        graph_info = {}
        try:
            run_query, _ = get_db()
            # Look up disease-symptom relationships from graph
            if top_disease not in ["Uncertain — Consult Veterinarian", "Rare — Consult Veterinarian"]:
                graph_result = run_query(
                    "MATCH (d:Disease {name: $name})-[r:HAS_SYMPTOM]->(s:Symptom) "
                    "RETURN s.name AS symptom, r.count AS frequency "
                    "ORDER BY r.count DESC",
                    {"name": top_disease}
                )
                graph_info["commonSymptoms"] = [
                    {"symptom": r["symptom"], "frequency": r["frequency"]}
                    for r in graph_result
                ]

                # How many animals in the DB have this disease
                count_result = run_query(
                    "MATCH (a:Animal)-[:PREDICTED_WITH]->(d:Disease {name: $name}) "
                    "RETURN count(a) AS count",
                    {"name": top_disease}
                )
                graph_info["knownCases"] = count_result[0]["count"] if count_result else 0
        except Exception:
            pass  # Graph enrichment is optional

        # NOTE: We deliberately do NOT write predictions back to the graph.
        # Model predictions are not confirmed diagnoses — storing them would mix
        # ground-truth seed data with live guesses and create phantom Disease
        # nodes (e.g. the guardrail labels). Diagnosis stays read-only.

        # Ask the graph how distinguishable this symptom set is. This is what
        # turns "confidence 17.6%" into an actual reason.
        graph_evidence = get_graph_evidence(matched)

        return jsonify({
            "disease": top_disease,
            "confidence": round(float(top_conf) * 100, 1),
            "allPredictions": [
                {"disease": d, "confidence": round(float(p) * 100, 1)}
                for d, p in ranked if d not in GUARDRAIL_LABELS
            ][:5],
            "matchedSymptoms": matched,
            "unmatchedSymptoms": unmatched,
            "drivingSymptoms": driving,
            "graphInfo": graph_info,
            "graphEvidence": graph_evidence,
            "disclaimer": "This is AI-assisted decision support only, not a veterinary diagnosis. "
                         "Always consult a qualified veterinarian for treatment decisions."
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# GRAPH EVIDENCE
# ═══════════════════════════════════════════════════════════════
def get_graph_evidence(symptoms):
    """
    Ask the knowledge graph how DISTINGUISHABLE this symptom set is.

    Finds every animal exhibiting all of the given symptoms, and reports which
    diseases those animals actually have. Three outcomes:

      distinctive : the symptoms point at a single disease
      ambiguous   : several diseases share this pattern -> symptoms alone
                    cannot separate them
      unseen      : no animal in the reference data shows this combination

    This is a genuine Cypher query against Neo4j at request time. It does NOT
    feed the model — evaluation showed graph-derived features reduced accuracy
    (see GRAPH_FEATURES.md). It exists to EXPLAIN the model's confidence:
    "these symptoms match 10 diseases" is a far better reason to defer to a
    veterinarian than "confidence is 17.6%".
    """
    if not symptoms:
        return None

    try:
        run_query, _ = get_db()
        # Count how many of the requested symptoms each animal exhibits, keep
        # the animals exhibiting ALL of them, then report their diseases.
        #
        # Deliberately plain Cypher (no pattern comprehensions) so it behaves
        # consistently across Cypher versions.
        rows = run_query(
            "MATCH (a:Animal)-[:EXHIBITS]->(s:Symptom) "
            "WHERE s.name IN $symptoms "
            "WITH a, count(DISTINCT s.name) AS matched "
            "WHERE matched = $n "
            "MATCH (a)-[:PREDICTED_WITH]->(d:Disease) "
            "RETURN d.name AS disease, count(DISTINCT a) AS cases "
            "ORDER BY cases DESC",
            {"symptoms": list(symptoms), "n": len(set(symptoms))},
        )
    except Exception:
        return None  # graph enrichment is optional; never break diagnosis

    matches = [{"disease": r["disease"], "cases": r["cases"]} for r in rows]
    total_cases = sum(m["cases"] for m in matches)
    n = len(matches)

    if n == 0:
        mode = "unseen"
        message = (
            "This combination of symptoms does not appear in the reference data. "
            "The prediction is extrapolating beyond what it has seen — treat it "
            "with particular caution."
        )
    elif n == 1:
        mode = "distinctive"
        only = matches[0]
        message = (
            f"This pattern is distinctive: in the knowledge graph it appears only "
            f"with {only['disease']} ({only['cases']} "
            f"case{'' if only['cases'] == 1 else 's'})."
        )
        if only["cases"] < 3:
            message += " Very few reference cases, so confidence should stay low."
    else:
        mode = "ambiguous"
        message = (
            f"These symptoms match {n} different diseases across {total_cases} "
            f"animals in the knowledge graph. Symptoms alone cannot separate them "
            f"— veterinary examination is needed to narrow it down."
        )

    evidence = {
        "mode": mode,
        "matchCount": n,
        "totalCases": total_cases,
        "matches": matches[:6],
        "message": message,
    }

    # When the result is ambiguous, work out which ADDITIONAL observation would
    # split the remaining candidates most effectively.
    if mode == "ambiguous":
        evidence["suggestions"] = suggest_next_checks(matches, symptoms)

    return evidence


def suggest_next_checks(matches, already_selected, top_n=3):
    """
    Differential narrowing: which unobserved symptom best separates the
    remaining candidate diseases?

    For each symptom not yet selected, the candidates split into those that
    present with it and those that don't. A symptom shared by ALL candidates
    (or none) splits nothing and is skipped. The best check leaves the fewest
    candidates on average — weighting each disease by how many real cases it
    has, so ruling out a common disease counts for more than a rare one.

    This exists because the evaluation established that symptoms alone cap
    accuracy at ~40% (see GRAPH_FEATURES.md). Rather than only reporting that
    dead end, the app can tell the user how to escape it.
    """
    if len(matches) < 2:
        return []

    candidate_names = [m["disease"] for m in matches]
    cases = {m["disease"]: m["cases"] for m in matches}
    total = sum(cases.values()) or 1

    try:
        run_query, _ = get_db()
        rows = run_query(
            "MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom) "
            "WHERE d.name IN $diseases "
            "RETURN d.name AS disease, collect(s.name) AS symptoms",
            {"diseases": candidate_names},
        )
    except Exception:
        return []

    profile = {r["disease"]: set(r["symptoms"]) for r in rows}
    selected = set(already_selected)

    # Every symptom any candidate presents with, minus those already observed
    pool = set()
    for syms in profile.values():
        pool |= syms
    pool -= selected

    scored = []
    for sym in sorted(pool):
        yes = [d for d in candidate_names if sym in profile.get(d, set())]
        no = [d for d in candidate_names if sym not in profile.get(d, set())]
        if not yes or not no:
            continue  # present in all candidates, or none — splits nothing

        p_yes = sum(cases[d] for d in yes) / total
        expected = p_yes * len(yes) + (1 - p_yes) * len(no)

        scored.append({
            "symptom": sym,
            "ifPresent": len(yes),
            "ifAbsent": len(no),
            "expectedRemaining": round(expected, 1),
            "eliminates": round(len(candidate_names) - expected, 1),
        })

    scored.sort(key=lambda x: x["expectedRemaining"])
    return scored[:top_n]



# ═══════════════════════════════════════════════════════════════
# MILK YIELD ESTIMATION
# ═══════════════════════════════════════════════════════════════
@api_bp.route("/milk-estimate", methods=["POST"])
def milk_estimate():
    """
    Estimate daily milk yield from animal attributes.

    Body: { "breed": "Holstein", "age": 4, "weight": 600 }
    Returns: { "estimatedYield", "unit", "modelInfo" }
    """
    try:
        if milk_artifact is None:
            return jsonify({"error": "Milk model not loaded"}), 503

        data = request.get_json()
        breed = data.get("breed", "")
        age = data.get("age")
        weight = data.get("weight")

        if age is None or weight is None:
            return jsonify({"error": "age and weight are required"}), 400

        # Encode breed
        le = milk_artifact["breed_encoder"]
        known_breeds = milk_artifact["breeds_known"]

        if breed in known_breeds:
            breed_encoded = le.transform([breed])[0]
        else:
            # Unknown breed — use median encoding
            breed_encoded = len(known_breeds) // 2

        features = np.array([[breed_encoded, age, weight]])
        prediction = milk_artifact["model"].predict(features)[0]
        prediction = max(0, round(float(prediction), 1))

        yield_range = milk_artifact["yield_range"]

        return jsonify({
            "estimatedYield": prediction,
            "unit": "L/day",
            "breed": breed,
            "knownBreeds": known_breeds,
            "breedRecognized": breed in known_breeds,
            "datasetRange": yield_range,
            "disclaimer": "Estimate based on breed, age, and weight only. "
                         "Actual yield depends on nutrition, lactation stage, health, and environment."
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# VOCABULARY (for frontend dropdowns)
# ═══════════════════════════════════════════════════════════════
@api_bp.route("/vocab", methods=["GET"])
def get_vocab():
    """Return symptoms, diseases, animal types for UI dropdowns."""
    if vocab is None:
        return jsonify({"error": "Vocabulary not loaded"}), 503
    return jsonify(vocab)


# ═══════════════════════════════════════════════════════════════
# GRAPH VISUALIZATION
# ═══════════════════════════════════════════════════════════════
@api_bp.route("/graph-data", methods=["GET"])
def graph_data():
    """
    Return nodes and links for D3/force-graph visualization.
    Optional ?type=Animal|Disease|Symptom to filter.
    """
    try:
        run_query, _ = get_db()
        node_type = request.args.get("type")

        if node_type:
            # Filtered: show nodes of that type + their immediate neighbors
            nodes_result = run_query(
                "MATCH (n) WHERE $type IN labels(n) "
                "OPTIONAL MATCH (n)-[r]-(m) "
                "RETURN DISTINCT "
                "  id(n) AS nodeId, labels(n)[0] AS label, "
                "  coalesce(n.animalId, n.name, n.animalType) AS name, "
                "  properties(n) AS props "
                "LIMIT 200",
                {"type": node_type}
            )
            rels_result = run_query(
                "MATCH (n)-[r]-(m) WHERE $type IN labels(n) "
                "RETURN DISTINCT id(startNode(r)) AS source, id(endNode(r)) AS target, "
                "  type(r) AS relationship "
                "LIMIT 500",
                {"type": node_type}
            )
        else:
            # Show a representative sample: all diseases + symptoms + some animals
            nodes_result = run_query(
                "MATCH (n) WHERE n:Disease OR n:Symptom OR (n:Animal AND rand() < 0.3) "
                "RETURN DISTINCT "
                "  id(n) AS nodeId, labels(n)[0] AS label, "
                "  coalesce(n.animalId, n.name) AS name, "
                "  properties(n) AS props "
                "LIMIT 300"
            )
            rels_result = run_query(
                "MATCH (n)-[r]->(m) "
                "WHERE (n:Disease OR n:Symptom OR n:Animal) "
                "AND (m:Disease OR m:Symptom OR m:Animal) "
                "RETURN DISTINCT id(n) AS source, id(m) AS target, "
                "  type(r) AS relationship "
                "LIMIT 800"
            )

        nodes = [
            {
                "id": r["nodeId"],
                "label": r["label"],
                "name": r["name"] or "unknown",
                "properties": dict(r["props"]) if r["props"] else {},
            }
            for r in nodes_result
        ]

        links = [
            {
                "source": r["source"],
                "target": r["target"],
                "relationship": r["relationship"],
            }
            for r in rels_result
        ]

        return jsonify({"nodes": nodes, "links": links})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# DISEASES
# ═══════════════════════════════════════════════════════════════
@api_bp.route("/graph-network", methods=["GET"])
def graph_network():
    """
    The disease <-> symptom network, for force-directed visualisation.

    Deliberately excludes Animal nodes: 146 identical-looking nodes add visual
    noise without adding meaning. The interesting structure is which diseases
    share which symptoms — that is what makes the diagnostic ambiguity visible.

    Cypher is kept intentionally simple (no pattern comprehensions) so it
    behaves consistently across Cypher versions.
    """
    try:
        run_query, _ = get_db()

        edges = run_query(
            "MATCH (d:Disease)-[r:HAS_SYMPTOM]->(s:Symptom) "
            "RETURN d.name AS disease, s.name AS symptom, r.count AS weight"
        )

        # How many animals carry each disease (node size)
        case_rows = run_query(
            "MATCH (a:Animal)-[:PREDICTED_WITH]->(d:Disease) "
            "RETURN d.name AS disease, count(a) AS cases"
        )
        cases = {r["disease"]: r["cases"] for r in case_rows}

        # How many animals exhibit each symptom (node size)
        sym_rows = run_query(
            "MATCH (a:Animal)-[:EXHIBITS]->(s:Symptom) "
            "RETURN s.name AS symptom, count(a) AS occurrences"
        )
        occurrences = {r["symptom"]: r["occurrences"] for r in sym_rows}

        # Build node list from whatever appears in the edges
        disease_names = sorted({e["disease"] for e in edges})
        symptom_names = sorted({e["symptom"] for e in edges})

        nodes = (
            [{"id": f"d:{n}", "label": n, "type": "disease",
              "value": cases.get(n, 0)} for n in disease_names]
            + [{"id": f"s:{n}", "label": n, "type": "symptom",
                "value": occurrences.get(n, 0)} for n in symptom_names]
        )

        links = [{
            "source": f"d:{e['disease']}",
            "target": f"s:{e['symptom']}",
            "weight": e["weight"] or 1,
        } for e in edges]

        # Degree = how many symptoms a disease has, and vice versa.
        # A symptom shared by many diseases is a poor discriminator.
        degree = {}
        for l in links:
            degree[l["source"]] = degree.get(l["source"], 0) + 1
            degree[l["target"]] = degree.get(l["target"], 0) + 1
        for n in nodes:
            n["degree"] = degree.get(n["id"], 0)

        return jsonify({
            "nodes": nodes,
            "links": links,
            "summary": {
                "diseases": len(disease_names),
                "symptoms": len(symptom_names),
                "connections": len(links),
            },
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route("/diseases", methods=["GET"])
def get_diseases():
    """List all diseases with symptom counts."""
    try:
        run_query, _ = get_db()
        results = run_query(
            "MATCH (d:Disease) "
            "OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom) "
            "RETURN d.name AS name, count(s) AS symptomCount "
            "ORDER BY d.name"
        )
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/diseases/<name>", methods=["GET"])
def get_disease(name):
    """Get disease details with symptoms and affected animals."""
    try:
        run_query, _ = get_db()
        syms = run_query(
            "MATCH (d:Disease {name: $name})-[r:HAS_SYMPTOM]->(s:Symptom) "
            "RETURN s.name AS symptom, r.count AS frequency "
            "ORDER BY r.count DESC",
            {"name": name}
        )
        animals = run_query(
            "MATCH (a:Animal)-[:PREDICTED_WITH]->(d:Disease {name: $name}) "
            "RETURN a.animalId AS id, a.animalType AS type, a.breed AS breed "
            "ORDER BY a.animalId",
            {"name": name}
        )
        return jsonify({
            "name": name,
            "symptoms": syms,
            "affectedAnimals": animals,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
