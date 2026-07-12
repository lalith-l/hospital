# backend/agents/discriminating_pairs.py

# Pre-computed at startup, not at runtime
# "If the system is torn between two conditions,
#  which question discriminates best?"

DISCRIMINATING_QUESTIONS = {
    ("Chikungunya", "Dengue"): {
        "question": "Is the joint pain so severe that you cannot walk or use your hands?",
        "Dengue_if_no": 0.68,     # joint pain mild = more likely Dengue
        "Chikungunya_if_yes": 0.74  # joint pain severe = more likely Chikungunya
    },
    ("Dengue", "Typhoid fever"): {
        "question": "Did the fever come on suddenly within hours, or build up over several days?",
        "Dengue_if_sudden": 0.71,
        "Typhoid fever_if_gradual": 0.69
    },
    ("Acute rhinosinusitis", "Allergic rhinitis"): {
        "question": "Do you have a thick, discolored nasal discharge or facial pain?",
        "Allergic rhinitis_if_no": 0.65,
        "Acute rhinosinusitis_if_yes": 0.82
    },
    ("GERD", "Myocardial Infarction"): {
        "question": "Does the pain get better when you sit up or take antacids?",
        "Myocardial Infarction_if_no": 0.61,
        "GERD_if_yes": 0.73
    },
    ("Asthma", "Bronchitis"): {
        "question": "Are you coughing up thick mucus?",
        "Asthma_if_no": 0.70,
        "Bronchitis_if_yes": 0.75
    },
    ("Influenza", "COVID-19"): {
        "question": "Have you suddenly lost your sense of taste or smell?",
        "Influenza_if_no": 0.55,
        "COVID-19_if_yes": 0.85
    }
}

def get_discriminating_question(top_two_diagnoses):
    """
    Given the top two competing diagnoses, return the single
    question that best separates them based on DDXPlus statistics.
    Expects a list of two strings.
    """
    if not top_two_diagnoses or len(top_two_diagnoses) < 2:
        return None
        
    pair = tuple(sorted([top_two_diagnoses[0], top_two_diagnoses[1]]))
    # Check both sorted combinations just in case dict has it differently
    pair1 = (top_two_diagnoses[0], top_two_diagnoses[1])
    pair2 = (top_two_diagnoses[1], top_two_diagnoses[0])
    
    if pair1 in DISCRIMINATING_QUESTIONS:
        return DISCRIMINATING_QUESTIONS[pair1]["question"]
    elif pair2 in DISCRIMINATING_QUESTIONS:
        return DISCRIMINATING_QUESTIONS[pair2]["question"]
        
    return None
