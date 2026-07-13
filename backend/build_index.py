import os
import ast
import json
import faiss
import numpy as np
import pandas as pd
import pickle
from sklearn.preprocessing import MultiLabelBinarizer

DATA_DIR = "ddxplus_data"

def clean_evidences(evidence_list):
    """Strips the specific values (e.g., _@_V_180) from evidences, keeping only the base code."""
    cleaned = set()
    for ev in evidence_list:
        base_code = ev.split("_@_")[0]
        cleaned.add(base_code)
    return list(cleaned)

def main():
    print("Loading evidences dictionary...")
    with open(os.path.join(DATA_DIR, "release_evidences.json"), "r") as f:
        evs = json.load(f)
    
    # The 223 unique symptoms/evidences in DDXPlus
    all_symptoms = sorted(list(evs.keys()))
    print(f"Total unique symptoms in vocabulary: {len(all_symptoms)}")

    print("Loading validate split...")
    df = pd.read_csv(os.path.join(DATA_DIR, "validate.csv"), nrows=40000)
    print(f"Loaded {len(df)} records.")

    print("Parsing evidences...")
    # The EVIDENCES column contains string representations of lists
    df["parsed_evidences"] = df["EVIDENCES"].apply(ast.literal_eval)
    
    # Strip values from evidences
    df["clean_evidences"] = df["parsed_evidences"].apply(clean_evidences)

    print("Vectorizing...")
    # Initialize MultiLabelBinarizer with exact classes so the vector is always 223-dim
    mlb = MultiLabelBinarizer(classes=all_symptoms)
    
    # Fit and transform (fit is essentially hardcoded by classes)
    binary_vectors = mlb.fit_transform(df["clean_evidences"]).astype(np.float32)
    
    print(f"Vectors shape: {binary_vectors.shape}")

    print("Building FAISS index...")
    # IndexFlatL2 measures L2 distance, which for binary vectors effectively measures Hamming-like distance
    index = faiss.IndexFlatL2(len(all_symptoms))
    index.add(binary_vectors)

    index_path = os.path.join(DATA_DIR, "ddxplus.index")
    faiss.write_index(index, index_path)
    print(f"FAISS index saved to {index_path}")

    print("Saving diagnoses...")
    # Save the PATHOLOGY labels
    diagnoses = df["PATHOLOGY"].values
    diagnoses_path = os.path.join(DATA_DIR, "diagnoses.npy")
    np.save(diagnoses_path, diagnoses)
    print(f"Diagnoses saved to {diagnoses_path}")

    # Save the binarizer
    mlb_path = os.path.join(DATA_DIR, "mlb.pkl")
    with open(mlb_path, "wb") as f:
        pickle.dump(mlb, f)
    print(f"MultiLabelBinarizer saved to {mlb_path}")

    print("Done!")

if __name__ == "__main__":
    main()
