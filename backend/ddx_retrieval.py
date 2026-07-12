import os
import faiss
import pickle
import numpy as np
from typing import List, Dict

DATA_DIR = "ddxplus_data"

# Global state for fast loaded index
_index = None
_diagnoses = None
_mlb = None

def _load_resources():
    global _index, _diagnoses, _mlb
    if _index is None:
        index_path = os.path.join(DATA_DIR, "ddxplus.index")
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"FAISS index not found at {index_path}. Please run build_index.py first.")
        _index = faiss.read_index(index_path)

    if _diagnoses is None:
        diagnoses_path = os.path.join(DATA_DIR, "diagnoses.npy")
        _diagnoses = np.load(diagnoses_path, allow_pickle=True)

    if _mlb is None:
        mlb_path = os.path.join(DATA_DIR, "mlb.pkl")
        with open(mlb_path, "rb") as f:
            _mlb = pickle.load(f)

def lookup_symptoms(symptoms: List[str], k: int = 50) -> Dict:
    """
    Search the FAISS index for the k nearest patients with these exact symptoms.
    Returns the diagnosis probabilities and a confidence metric.
    """
    if not symptoms:
        return {
            "probabilities": [],
            "confidence": "low",
            "message": "No specific DDXPlus symptoms extracted."
        }

    _load_resources()

    # Filter input symptoms to only those present in the DDXPlus vocabulary
    valid_symptoms = [s for s in symptoms if s in _mlb.classes_]
    
    if not valid_symptoms:
        return {
            "probabilities": [],
            "confidence": "low",
            "message": "No valid DDXPlus symptoms found."
        }

    # Vectorize
    vector = _mlb.transform([valid_symptoms]).astype(np.float32)

    # Search FAISS
    distances, indices = _index.search(vector, k)
    
    # Get the diagnoses for the top k neighbors
    neighbor_diagnoses = _diagnoses[indices[0]]
    
    # Compute probabilities
    counts = {}
    for diag in neighbor_diagnoses:
        counts[diag] = counts.get(diag, 0) + 1
        
    # Sort and format
    probs = []
    for diag, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        probs.append({
            "condition": diag,
            "probability": round(count / k, 3)
        })
        
    # Apply confidence thresholding logic
    top_prob = probs[0]["probability"] if probs else 0.0
    
    if top_prob < 0.15:
        confidence = "low"
    elif top_prob < 0.35:
        confidence = "medium"
    else:
        confidence = "high"

    # Only return top 5
    top_5_probs = probs[:5]

    return {
        "probabilities": top_5_probs,
        "confidence": confidence,
        "message": "Success"
    }
