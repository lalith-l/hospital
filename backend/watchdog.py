import random
from agents.intake_agent import IntakeAgent
from agents.diagnosis_agent import DiagnosisAgent

IRRELEVANT_PERTURBATIONS = [
    "I also painted my fence yesterday.",
    "My favorite color is blue.",
    "I had pasta for dinner last night.",
    "I watched a movie yesterday.",
    "My car needs an oil change."
]

def hallucination_watchdog(symptoms, primary_diagnosis, primary_confidence):
    perturbation = random.choice(IRRELEVANT_PERTURBATIONS)
    
    # We craft a fake conversation with the symptoms and the perturbation
    messages = [
        {"role": "user", "content": f"My symptoms are: {symptoms}. By the way, {perturbation}"}
    ]
    
    try:
        # Step 1: Extract symptoms with the perturbation
        extracted_data = IntakeAgent.extract_symptoms(messages)
        shadow_symptoms = extracted_data.get("symptoms", [])
        
        # Step 2: Compute diagnosis
        ddx_result = DiagnosisAgent.compute_differential(shadow_symptoms)
        probs = ddx_result.get("probabilities", [])
        
        shadow_diagnosis = "Unknown"
        shadow_confidence = 0.5
        
        if probs:
            shadow_diagnosis = probs[0].get("condition", "Unknown")
            shadow_confidence = probs[0].get("probability", 0.5)
            
        if shadow_diagnosis != primary_diagnosis and shadow_diagnosis != "Unknown":
            return {
                "hallucination_detected": True,
                "severity": "HIGH",
                "reason": f"Diagnosis changed from {primary_diagnosis} to {shadow_diagnosis} after irrelevant perturbation",
                "action": "FLAG_FOR_HUMAN_REVIEW"
            }
        
        confidence_delta = abs(primary_confidence - shadow_confidence)
        if confidence_delta > 0.15:
            return {
                "hallucination_detected": True,
                "severity": "MEDIUM", 
                "reason": f"Confidence shifted {confidence_delta:.2f} from irrelevant detail",
                "action": "LOWER_DISPLAYED_CONFIDENCE"
            }
            
        return {"hallucination_detected": False}
        
    except Exception as e:
        print(f"Watchdog error: {e}")
        return {"hallucination_detected": False, "error": str(e)}
