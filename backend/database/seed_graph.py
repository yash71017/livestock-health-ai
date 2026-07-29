"""
seed_graph.py — Seed Neo4j from cleaned data files.

Usage:
    python seed_graph.py                 # prints Cypher to stdout
    python seed_graph.py --execute       # runs against live Neo4j (needs .env)
    python seed_graph.py --file seed.cypher  # writes to file

The graph schema:
    (:Animal {animalId, animalType, breed, age, gender, weight})
    (:Disease {name})
    (:Symptom {name})
    (:MilkRecord {animalId, breed, age, weight, milkYield})
    
    (Animal)-[:EXHIBITS]->(Symptom)
    (Animal)-[:PREDICTED_WITH]->(Disease)
    (Animal)-[:HAS_MILK_RECORD]->(MilkRecord)
    (Disease)-[:HAS_SYMPTOM]->(Symptom)     // aggregated disease-symptom link
"""

import pandas as pd
import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")


def escape_cypher(s):
    """Escape single quotes for Cypher string literals."""
    if pd.isna(s):
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'")


def generate_cypher():
    """Generate complete Cypher seed script from cleaned data."""
    animals = pd.read_csv(os.path.join(DATA_DIR, "cleaned_animals.csv"))
    symptoms_rel = pd.read_csv(os.path.join(DATA_DIR, "cleaned_symptoms.csv"))
    disease_sym = pd.read_csv(os.path.join(DATA_DIR, "disease_symptom_map.csv"))
    milk = pd.read_csv(os.path.join(DATA_DIR, "cleaned_milk.csv"))
    vocab = json.load(open(os.path.join(DATA_DIR, "vocab.json")))

    lines = []
    lines.append("// ═══════════════════════════════════════════════════")
    lines.append("// Livestock AI Health — Neo4j Seed Script (auto-generated)")
    lines.append("// ═══════════════════════════════════════════════════")
    lines.append("")

    # ── Constraints ──
    lines.append("// ── Constraints ──")
    lines.append("CREATE CONSTRAINT animal_id IF NOT EXISTS FOR (a:Animal) REQUIRE a.animalId IS UNIQUE;")
    lines.append("CREATE CONSTRAINT disease_name IF NOT EXISTS FOR (d:Disease) REQUIRE d.name IS UNIQUE;")
    lines.append("CREATE CONSTRAINT symptom_name IF NOT EXISTS FOR (s:Symptom) REQUIRE s.name IS UNIQUE;")
    lines.append("")

    # ── Symptom nodes ──
    lines.append("// ── Symptom nodes ──")
    for sym in vocab["symptoms"]:
        lines.append(f"MERGE (:Symptom {{name: '{escape_cypher(sym)}'}});")
    lines.append("")

    # ── Disease nodes ──
    lines.append("// ── Disease nodes ──")
    for dis in vocab["diseases"]:
        lines.append(f"MERGE (:Disease {{name: '{escape_cypher(dis)}'}});")
    lines.append("")

    # ── Animal nodes + relationships ──
    lines.append("// ── Animal nodes + EXHIBITS + PREDICTED_WITH ──")
    for _, row in animals.iterrows():
        aid = escape_cypher(row["Animal_Id"])
        atype = escape_cypher(row["Animal_Type"])
        breed = escape_cypher(row["Breed"])
        age = int(row["Age"])
        gender = escape_cypher(row["Gender"])
        weight = float(row["Weight"])
        disease = escape_cypher(row["Disease_Prediction"])

        lines.append(
            f"MERGE (a:Animal {{animalId: '{aid}'}}) "
            f"SET a.animalType = '{atype}', a.breed = '{breed}', "
            f"a.age = {age}, a.gender = '{gender}', a.weight = {weight};"
        )
        # Disease relationship
        lines.append(
            f"MATCH (a:Animal {{animalId: '{aid}'}}), (d:Disease {{name: '{disease}'}}) "
            f"MERGE (a)-[:PREDICTED_WITH]->(d);"
        )

    lines.append("")

    # ── EXHIBITS relationships (animal → symptom) ──
    lines.append("// ── EXHIBITS relationships ──")
    for _, row in symptoms_rel.iterrows():
        aid = escape_cypher(row["Animal_Id"])
        sym = escape_cypher(row["Symptom"])
        lines.append(
            f"MATCH (a:Animal {{animalId: '{aid}'}}), (s:Symptom {{name: '{sym}'}}) "
            f"MERGE (a)-[:EXHIBITS]->(s);"
        )
    lines.append("")

    # ── HAS_SYMPTOM relationships (disease → symptom, aggregated) ──
    lines.append("// ── Disease-Symptom aggregate links ──")
    for _, row in disease_sym.iterrows():
        dis = escape_cypher(row["Disease"])
        sym = escape_cypher(row["Symptom"])
        count = int(row["Count"])
        lines.append(
            f"MATCH (d:Disease {{name: '{dis}'}}), (s:Symptom {{name: '{sym}'}}) "
            f"MERGE (d)-[r:HAS_SYMPTOM]->(s) SET r.count = {count};"
        )
    lines.append("")

    # ── Milk records ──
    lines.append("// ── Milk records ──")
    for _, row in milk.iterrows():
        aid = escape_cypher(row["Animal_Id"])
        breed = escape_cypher(row["Breed"])
        age = int(row["Age"])
        weight = int(row["Weight"])
        milk_yield = float(row["Milk_Yield(L/day)"])
        lines.append(
            f"MERGE (m:MilkRecord {{animalId: '{aid}'}}) "
            f"SET m.breed = '{breed}', m.age = {age}, m.weight = {weight}, "
            f"m.milkYield = {milk_yield};"
        )
        lines.append(
            f"MATCH (a:Animal {{animalId: '{aid}'}}), (m:MilkRecord {{animalId: '{aid}'}}) "
            f"MERGE (a)-[:HAS_MILK_RECORD]->(m);"
        )
    lines.append("")

    return "\n".join(lines)


def execute_against_neo4j(cypher_text):
    """Execute the seed script against a live Neo4j instance."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("ERROR: neo4j driver not installed. Run: pip install neo4j")
        sys.exit(1)

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")

    if not uri or not password:
        print("ERROR: NEO4J_URI and NEO4J_PASSWORD must be set in .env")
        sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    print(f"Connecting to {uri}...")

    # Clear existing data first
    with driver.session() as session:
        print("Clearing existing data...")
        session.run("MATCH (n) DETACH DELETE n")

    # Execute statements one at a time.
    #
    # NOTE: comments must be stripped BEFORE splitting on ";". Splitting first
    # produces chunks like "// header\nMERGE (...)" which begin with "//" — a
    # naive comment filter then discards the first real statement after every
    # header. That silently dropped one node of each type (and every
    # relationship depending on them) in an earlier version.
    code_only = "\n".join(
        line for line in cypher_text.splitlines()
        if not line.strip().startswith("//")
    )
    statements = [s.strip() for s in code_only.split(";") if s.strip()]
    total = len(statements)

    with driver.session() as session:
        for i, stmt in enumerate(statements):
            if i % 50 == 0:
                print(f"  Executing {i}/{total}...")
            try:
                session.run(stmt)
            except Exception as e:
                print(f"  ERROR at statement {i}: {e}")
                print(f"  Statement: {stmt[:200]}")
                # Continue — some constraint statements may fail if already exist

    print(f"Done. Executed {total} statements.")

    # Verify
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY label")
        print("\nVerification — node counts:")
        for record in result:
            print(f"  {record['label']}: {record['cnt']}")

        result = session.run("MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt ORDER BY rel")
        print("Relationship counts:")
        for record in result:
            print(f"  {record['rel']}: {record['cnt']}")

    driver.close()


if __name__ == "__main__":
    cypher = generate_cypher()

    if "--execute" in sys.argv:
        execute_against_neo4j(cypher)
    elif "--file" in sys.argv:
        idx = sys.argv.index("--file")
        path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "seed.cypher"
        with open(path, "w") as f:
            f.write(cypher)
        print(f"Written to {path} ({len(cypher.splitlines())} lines)")
    else:
        print(cypher)