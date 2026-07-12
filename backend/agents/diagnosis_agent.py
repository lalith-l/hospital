from typing import List, Dict
import ddx_retrieval

class DiagnosisAgent:
    """Agent 2: Queries DDXPlus FAISS and computes differentials."""

    @staticmethod
    def compute_differential(symptoms: List[str]) -> Dict:
        """
        Takes a list of DDXPlus symptom codes and returns differential diagnosis.
        """
        # Call the existing FAISS logic
        result = ddx_retrieval.lookup_symptoms(symptoms)
        
        # Apply any geographical priors here if needed in the future
        # For now, it just wraps the FAISS retrieval.
        return result
