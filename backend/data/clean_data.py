"""
clean_data.py — Master data cleaning pipeline
Reads raw uploaded data, standardises names, filters to livestock,
produces clean CSVs for Neo4j seeding and ML training.

Run: python clean_data.py
Outputs: cleaned_animals.csv, cleaned_symptoms.csv, cleaned_diseases.csv,
         cleaned_milk.csv, disease_symptom_map.csv, ml_training_data.csv
"""

import pandas as pd
import os
import json
from collections import Counter

RAW_DIR = os.environ.get("RAW_DATA_DIR", "raw")
OUT_DIR = os.environ.get("CLEAN_DATA_DIR", "cleaned")
REPORT_PATH = os.path.join(OUT_DIR, "data_quality_report.md")

# ── SCOPE DECISION ──────────────────────────────────────────────
# Livestock only. Dogs, Cats, Horses, Pigs, Rabbits are out of scope.
# No Buffalo in the source data, but schema supports it for future use.
LIVESTOCK_TYPES = {"Cow", "Buffalo", "Goat", "Sheep"}

# ── DISEASE NAME STANDARDISATION ────────────────────────────────
# These map messy/duplicate names → one canonical name per disease.
# Source: manual review of all 136 unique labels in the dataset.
DISEASE_CANONICAL = {
    # Bluetongue cluster (5 spellings → 1)
    "Blue Tongue": "Bluetongue",
    "Blue Tongue Disease": "Bluetongue",
    "Blue Tongue Virus": "Bluetongue",
    "Bluetongue Virus": "Bluetongue",
    "Bluetongue": "Bluetongue",
    # Foot and Mouth (2 spellings)
    "Foot and Mouth Disease": "Foot and Mouth Disease",
    "Foot-and-Mouth Disease": "Foot and Mouth Disease",
    # Johne's Disease
    "Johne's Disease": "Johne's Disease",
    "Bovine Johne's Disease": "Johne's Disease",
    # Scrapie
    "Scrapie": "Scrapie",
    "Scrapie Disease": "Scrapie",
    # Mastitis
    "Mastitis": "Mastitis",
    "Bovine Mastitis": "Mastitis",
    # Coccidiosis
    "Coccidiosis": "Coccidiosis",
    "Bovine Coccidiosis": "Coccidiosis",
    # Caprine Arthritis Encephalitis cluster
    "Caprine Arthritis Encephalitis": "Caprine Arthritis Encephalitis",
    "Caprine Arthritis Encephalitis Virus": "Caprine Arthritis Encephalitis",
    "Caprine Arthritis": "Caprine Arthritis Encephalitis",
    "Caprine Viral Arthritis": "Caprine Arthritis Encephalitis",
    # Tuberculosis
    "Tuberculosis": "Bovine Tuberculosis",
    "Bovine Tuberculosis": "Bovine Tuberculosis",
    # Pneumonia (generic → keep as-is for livestock)
    "Pneumonia": "Pneumonia",
    "Bovine Pneumonia": "Bovine Pneumonia",
    # Pasteurellosis
    "Pasteurellosis": "Pasteurellosis",
    # Caseous Lymphadenitis
    "Caseous Lymphadenitis": "Caseous Lymphadenitis",
    # Respiratory Syncytial Virus
    "Respiratory Syncytial Virus": "Bovine Respiratory Syncytial Virus",
    "Bovine Respiratory Syncytial Virus": "Bovine Respiratory Syncytial Virus",
    # BRD cluster
    "Bovine Respiratory Disease": "Bovine Respiratory Disease",
    "Bovine Respiratory Disease Complex": "Bovine Respiratory Disease",
}

# ── SYMPTOM STANDARDISATION ─────────────────────────────────────
SYMPTOM_CANONICAL = {
    "Appetite Loss": "Loss of Appetite",
    "Loss of Appetite": "Loss of Appetite",
    "Reduced Appetite": "Loss of Appetite",
    "Reduced Milk Yield": "Decreased Milk Yield",
    "Reduced Milk Production": "Decreased Milk Yield",
    "Decreased Milk Yield": "Decreased Milk Yield",
    "Reduced Wool Growth": "Reduced Wool Production",
    "Reduced Wool Production": "Reduced Wool Production",
    "No": None,  # "No" is not a symptom — it means missing
}


def _find_file(candidates):
    """Return the first filename in RAW_DIR that matches any candidate (case-insensitive)."""
    import glob
    existing = os.listdir(RAW_DIR)
    lower_map = {f.lower(): f for f in existing}
    for cand in candidates:
        if cand.lower() in lower_map:
            return os.path.join(RAW_DIR, lower_map[cand.lower()])
    # Fuzzy fallback: match by keyword
    return None


def _read_any(path):
    """Read xlsx or csv based on extension."""
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


def load_raw():
    """
    Load the two required data files.

    Only TWO files are needed:
      1. The master prediction table (animal + symptoms + disease)
      2. The milk yield table

    Accepts several possible filenames so you don't have to rename anything.
    """
    # ── 1. Master prediction table ──
    master_path = _find_file([
        "cleaned_animal_disease_prediction_2_csv_csv.xlsx",
        "Animal_Disease_Prediction_Reduced_csv.xlsx",
        "ANIMAL_reduced.xlsx",
        "cleaned_animal_disease_prediction_2.xlsx",
    ])
    if master_path is None:
        # Fuzzy: any file with 'reduced' or 'prediction' in the name
        for f in os.listdir(RAW_DIR):
            if "reduced" in f.lower() or "prediction" in f.lower():
                master_path = os.path.join(RAW_DIR, f)
                break
    if master_path is None:
        raise FileNotFoundError(
            f"Could not find the master prediction table in {RAW_DIR}. "
            f"Expected a file with 'prediction' or 'reduced' in the name. "
            f"Found: {os.listdir(RAW_DIR)}"
        )
    print(f"  Master table: {os.path.basename(master_path)}")
    prediction = _read_any(master_path)

    # ── 2. Milk yield table ──
    milk_path = _find_file([
        "AnimalMilk_relationship_.csv",
        "AnimalMilk(relationship).xlsx",
        "AnimalMilk_relationship.csv",
        "MilkData_csv_csv.xlsx",
    ])
    if milk_path is None:
        for f in os.listdir(RAW_DIR):
            if "milk" in f.lower():
                milk_path = os.path.join(RAW_DIR, f)
                break
    if milk_path is None:
        print("  WARNING: No milk file found. Milk yield model will be skipped.")
        rel_milk = pd.DataFrame(columns=["Animal_Id", "Breed", "Age", "Weight", "Milk_Yield(L/day)"])
    else:
        print(f"  Milk table: {os.path.basename(milk_path)}")
        rel_milk = _read_any(milk_path)

    return prediction, rel_milk


def build_master(animals, diseases, prediction):
    """
    Build a single master table: one row per animal with demographics,
    symptoms, and disease label.
    """
    # The prediction file already has everything we need
    df = prediction.copy()

    # Create a clean Animal_Id: "A1" through "A431"
    # The Animal_csv uses integer IDs; relationship files use "A1" format
    df["Animal_Id"] = ["A" + str(i + 1) for i in range(len(df))]

    # Drop the messy Cow_ID column
    df = df.drop(columns=["Cow_ID"], errors="ignore")

    return df


def filter_livestock(df):
    """Keep only livestock species."""
    before = len(df)
    df = df[df["Animal_Type"].isin(LIVESTOCK_TYPES)].copy()
    after = len(df)
    print(f"  Scope filter: {before} → {after} rows (dropped {before - after} non-livestock)")
    return df


def standardise_diseases(df):
    """Apply canonical disease names."""
    raw_diseases = df["Disease_Prediction"].unique()
    unmapped = [d for d in raw_diseases if d not in DISEASE_CANONICAL]
    if unmapped:
        print(f"  Warning: {len(unmapped)} diseases not in canonical map (kept as-is): {unmapped}")

    df["Disease_Prediction"] = df["Disease_Prediction"].map(
        lambda d: DISEASE_CANONICAL.get(d, d)
    )
    print(f"  Diseases after standardisation: {df['Disease_Prediction'].nunique()} unique")
    return df


def standardise_symptoms(df):
    """Apply canonical symptom names, drop 'No' (missing marker)."""
    sym_cols = ["Symptom_1", "Symptom_2", "Symptom_3", "Symptom_4"]
    for col in sym_cols:
        df[col] = df[col].map(lambda s: SYMPTOM_CANONICAL.get(s, s) if pd.notna(s) else None)
    # Count how many had "No" mapped to None
    return df


def validate_ranges(df):
    """Flag domain-impossible values."""
    issues = []
    # Age: livestock 0-25 years is plausible
    bad_age = df[(df["Age"] < 0) | (df["Age"] > 25)]
    if len(bad_age):
        issues.append(f"  Age out of range [0,25]: {len(bad_age)} rows")

    # Weight: livestock 5-1500 kg
    bad_wt = df[(df["Weight"] < 5) | (df["Weight"] > 1500)]
    if len(bad_wt):
        issues.append(f"  Weight out of range [5,1500kg]: {len(bad_wt)} rows")

    if issues:
        for i in issues:
            print(i)
    else:
        print("  Domain validation: all values in plausible ranges")
    return df


def build_symptom_list(df):
    """Build a deduplicated symptom set per animal."""
    sym_cols = ["Symptom_1", "Symptom_2", "Symptom_3", "Symptom_4"]
    records = []
    for _, row in df.iterrows():
        syms = set()
        for col in sym_cols:
            if pd.notna(row[col]) and row[col] is not None:
                syms.add(row[col])
        for s in sorted(syms):
            records.append({
                "Animal_Id": row["Animal_Id"],
                "Symptom": s,
            })
    return pd.DataFrame(records)


def build_disease_symptom_map(df):
    """Build disease → symptom mapping with co-occurrence counts."""
    sym_cols = ["Symptom_1", "Symptom_2", "Symptom_3", "Symptom_4"]
    records = []
    for _, row in df.iterrows():
        disease = row["Disease_Prediction"]
        for col in sym_cols:
            if pd.notna(row[col]) and row[col] is not None:
                records.append({
                    "Disease": disease,
                    "Symptom": row[col],
                    "Animal_Id": row["Animal_Id"],
                })
    map_df = pd.DataFrame(records)
    # Aggregate: how often each symptom appears with each disease
    agg = map_df.groupby(["Disease", "Symptom"]).size().reset_index(name="Count")
    return map_df, agg


def build_ml_training(df):
    """
    Build ML training data: one row per animal with binary symptom columns
    and the disease label.
    """
    sym_cols = ["Symptom_1", "Symptom_2", "Symptom_3", "Symptom_4"]
    # Collect all unique symptoms
    all_syms = set()
    for col in sym_cols:
        all_syms.update(df[col].dropna().unique())
    all_syms = sorted(all_syms)

    # Build binary matrix
    rows = []
    for _, row in df.iterrows():
        animal_syms = set()
        for col in sym_cols:
            if pd.notna(row[col]) and row[col] is not None:
                animal_syms.add(row[col])
        r = {
            "Animal_Id": row["Animal_Id"],
            "Animal_Type": row["Animal_Type"],
            "Breed": row["Breed"],
            "Age": row["Age"],
            "Weight": row["Weight"],
        }
        for s in all_syms:
            r[f"sym_{s}"] = 1 if s in animal_syms else 0
        r["Disease"] = row["Disease_Prediction"]
        rows.append(r)

    return pd.DataFrame(rows)


def clean_milk(milk_raw, rel_milk, livestock_ids):
    """Clean milk data, keeping only livestock animals."""
    # rel_milk has Animal_Id in "A3" format, milk_raw has COW_0001 format
    # We can only use rel_milk since it maps to our Animal_Id scheme
    milk = rel_milk.copy()
    milk = milk[milk["Animal_Id"].isin(livestock_ids)]
    print(f"  Milk records for livestock: {len(milk)}")
    return milk


def generate_report(master, livestock, ml_data, symptom_df, disease_agg, milk):
    """Generate data quality report as markdown."""
    lines = ["# Data Quality Report", ""]
    lines.append(f"Generated by `clean_data.py`")
    lines.append("")

    lines.append("## Raw Data Summary")
    lines.append(f"- Total animals in source: **{len(master)}**")
    lines.append(f"- Animal types: {sorted(master['Animal_Type'].unique())}")
    lines.append(f"- Raw disease labels: **{master['Disease_Prediction'].nunique()}**")
    lines.append("")

    lines.append("## After Cleaning")
    lines.append(f"- Livestock animals (Cow/Goat/Sheep): **{len(livestock)}**")
    lines.append(f"- Diseases after standardisation: **{livestock['Disease_Prediction'].nunique()}**")
    lines.append(f"- Unique symptoms: **{symptom_df['Symptom'].nunique()}**")
    lines.append(f"- Milk records: **{len(milk)}**")
    lines.append("")

    lines.append("## Disease Class Distribution")
    dist = livestock["Disease_Prediction"].value_counts()
    for d, c in dist.items():
        lines.append(f"- {d}: {c}")
    lines.append("")

    lines.append("## Symptom Inventory")
    sym_counts = symptom_df["Symptom"].value_counts()
    for s, c in sym_counts.items():
        lines.append(f"- {s}: {c} occurrences")
    lines.append("")

    lines.append("## Known Issues")
    lines.append("- **No Buffalo data** in source despite being in-scope")
    lines.append("- **Small dataset**: 146 livestock animals is below ideal for ML")
    lines.append("- **Severe class imbalance**: some diseases have only 1 sample")
    lines.append("- **Synthetic origin**: original data appears synthetically generated")
    lines.append("- **No milk biochemistry**: MilkData contains yield/herd metrics, NOT fat/protein/pH/SCC/bacteria")
    lines.append("- Disease labels with ≤2 samples cannot be reliably predicted")
    lines.append("")

    lines.append("## Transformations Applied")
    lines.append("1. Filtered to livestock species only (Cow, Goat, Sheep)")
    lines.append("2. Standardised disease names (e.g. 5 Bluetongue spellings → 1)")
    lines.append("3. Standardised symptom names (e.g. Appetite Loss/Reduced Appetite → Loss of Appetite)")
    lines.append("4. Removed 'No' pseudo-symptom (treated as missing)")
    lines.append("5. Unified Animal_Id format to 'A1'...'A431'")
    lines.append("6. Validated age [0-25] and weight [5-1500kg] ranges")
    lines.append("")

    return "\n".join(lines)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Loading raw data...")
    prediction, rel_milk = load_raw()

    print("Building master table...")
    master = build_master(None, None, prediction)

    print("Filtering to livestock...")
    livestock = filter_livestock(master)

    print("Standardising disease names...")
    livestock = standardise_diseases(livestock)

    print("Standardising symptom names...")
    livestock = standardise_symptoms(livestock)

    print("Validating ranges...")
    livestock = validate_ranges(livestock)

    print("Building symptom relationships...")
    symptom_df = build_symptom_list(livestock)

    print("Building disease-symptom map...")
    ds_raw, ds_agg = build_disease_symptom_map(livestock)

    print("Building ML training data...")
    ml_data = build_ml_training(livestock)

    print("Cleaning milk data...")
    livestock_ids = set(livestock["Animal_Id"].tolist())
    milk = clean_milk(None, rel_milk, livestock_ids)

    # Save everything
    livestock.to_csv(os.path.join(OUT_DIR, "cleaned_animals.csv"), index=False)
    symptom_df.to_csv(os.path.join(OUT_DIR, "cleaned_symptoms.csv"), index=False)
    ds_agg.to_csv(os.path.join(OUT_DIR, "disease_symptom_map.csv"), index=False)
    ml_data.to_csv(os.path.join(OUT_DIR, "ml_training_data.csv"), index=False)
    milk.to_csv(os.path.join(OUT_DIR, "cleaned_milk.csv"), index=False)

    # Save symptom and disease vocabularies as JSON (used by models + seed script)
    vocab = {
        "symptoms": sorted(symptom_df["Symptom"].unique().tolist()),
        "diseases": sorted(livestock["Disease_Prediction"].unique().tolist()),
        "animal_types": sorted(livestock["Animal_Type"].unique().tolist()),
    }
    with open(os.path.join(OUT_DIR, "vocab.json"), "w", encoding="utf-8") as f:
        json.dump(vocab, f, indent=2)

    report = generate_report(master, livestock, ml_data, symptom_df, ds_agg, milk)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nDone. Outputs in {OUT_DIR}/")
    print(f"  cleaned_animals.csv   ({len(livestock)} rows)")
    print(f"  cleaned_symptoms.csv  ({len(symptom_df)} rows)")
    print(f"  disease_symptom_map.csv ({len(ds_agg)} rows)")
    print(f"  ml_training_data.csv  ({len(ml_data)} rows)")
    print(f"  cleaned_milk.csv      ({len(milk)} rows)")
    print(f"  vocab.json")
    print(f"  data_quality_report.md")


if __name__ == "__main__":
    main()
