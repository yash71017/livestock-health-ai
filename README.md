# Livestock AI Health Monitor

A web-based decision-support tool for livestock disease diagnosis and milk yield estimation, backed by a Neo4j knowledge graph.

**Status:** Proof of concept / portfolio project. Not validated for clinical or commercial use.

## What It Does

- **Disease Diagnosis:** Select observed symptoms → ML model predicts probable disease with confidence score, enriched with knowledge-graph context (related symptoms, known cases).
- **Milk Yield Estimator:** Enter breed, age, and weight → predicted daily yield in litres.
- **Knowledge Graph:** Neo4j stores animals, diseases, symptoms, and their relationships. Graph data feeds back into predictions and is visualized in the UI.
- **Dashboard:** Live statistics from the graph database.

## Architecture

```
React (MUI)  →  Flask API  →  Neo4j AuraDB
                    ↓
              scikit-learn
         (disease classifier,
          yield regressor)
```

| Layer | Tech | Notes |
|-------|------|-------|
| Frontend | React 18, Material UI 5, react-router 6 | SPA with axios |
| Backend | Flask, flask-cors | Blueprint-based REST API |
| Database | Neo4j AuraDB Free | Cypher queries, graph relationships |
| ML | scikit-learn (LogisticRegression, RandomForest) | Calibrated probabilities |
| Data | 146 livestock records, 15 symptoms, 30 diseases | See DATA.md |

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Copy and fill in your Neo4j credentials
cp .env.example .env
# Edit .env with your AuraDB URI + password

# Clean data + train models
cd data && python clean_data.py && cd ..
python models/train_all.py

# Seed Neo4j (optional — if your instance is empty)
python database/seed_graph.py --execute

# Start the server
python app.py
```

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

Open http://localhost:3000

## Honest Limitations

See [DATA.md](backend/data/DATA.md) and [MODEL.md](backend/models/MODEL.md) for full details.

- **Synthetic data.** The training data is synthetic (431 animal records, 146 after filtering to livestock). Predictions are not clinically validated.
- **Small dataset.** 146 samples across 30 disease classes means some diseases have ≤2 training examples. Rare diseases are grouped into a "Consult Veterinarian" category.
- **Disease model accuracy: ~24%** on cross-validation (vs 14% baseline). Better than random but not reliable.
- **Milk model is yield-only.** The original design claimed biochemical quality assessment (fat, protein, pH, SCC, bacteria). No such data exists. The model honestly predicts yield from breed/age/weight.
- **No real-time monitoring.** This is a static prediction tool, not a monitoring system.
- **Graph features are storage + enrichment, not model input.** Neo4j stores relationships and enriches diagnosis results with context, but graph topology doesn't directly feed the ML features (yet — see Roadmap).

## Disclaimer

This tool is for educational and research purposes. It is **not** a substitute for professional veterinary diagnosis or treatment. Always consult a qualified veterinarian for animal health decisions.

## License

MIT
