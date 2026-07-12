# backend/agents/clinical_rules.py

import json

# Clinical question priority rules based on differential
CLINICAL_QUESTION_RULES = {
    "Myocardial Infarction": {
        "must_ask_first": [
            "Is the pain radiating to your left arm, jaw, or back?",
            "Are you sweating or feeling short of breath?",
            "Did it come on suddenly or gradually?"
        ],
        "ask_only_if": {},
        "never_ask_here": [
            "Do you have a rash?",
            "Any changes in bowel movements?",
            "Do you have joint pain?"
        ]
    },
    
    "Dengue": {
        "must_ask_first": [
            "How many days have you had the fever?",
            "Did it come on suddenly or gradually over days?"
        ],
        "ask_only_if": {
            "Do you have joint pain?": 
                ["Chikungunya", "Rheumatic fever"],
            "Do you have a rash?": 
                ["Dengue", "Measles", "Typhus"],
            "Have you recently traveled or been near stagnant water?":
                ["Malaria", "Dengue", "Leptospirosis"]
        },
        "never_ask_here": [
            "Is the pain radiating to your arm?",
            "Do you have chest tightness?"
        ]
    },
    "GERD": {
        "must_ask_first": [
            "Does the pain get worse after eating or when lying down?",
            "Do you have a sour taste in your mouth or feel acid backing up?"
        ],
        "ask_only_if": {},
        "never_ask_here": [
            "Do you have joint pain?",
            "Are you experiencing any numbness or tingling in your fingers?"
        ]
    },
    "Asthma": {
        "must_ask_first": [
            "Are you wheezing or making a whistling sound when you breathe?",
            "Is the breathing difficulty worse at night or early in the morning?"
        ],
        "ask_only_if": {},
        "never_ask_here": [
            "Do you have pain when you urinate?",
            "Have you noticed a rash anywhere?"
        ]
    },
    "Migraine": {
        "must_ask_first": [
            "Is the pain throbbing or pulsing, and is it mostly on one side of your head?",
            "Are you sensitive to light or sound right now?"
        ],
        "ask_only_if": {},
        "never_ask_here": [
            "Do you have a cough?",
            "Are your ankles swollen?"
        ]
    },
    "Appendicitis": {
        "must_ask_first": [
            "Did the pain start around your belly button and then move to the lower right side?",
            "Is the pain worse if you cough or walk?"
        ],
        "ask_only_if": {},
        "never_ask_here": [
            "Do you have a sore throat?",
            "Are your eyes red or itchy?"
        ]
    }
}

def validate_question(proposed_question, current_differential_top, questions_already_asked_str):
    """
    Check if proposed question is clinically appropriate
    for current diagnostic context.
    questions_already_asked_str should be a single string of all past questions to easily check substring.
    """
    rules = CLINICAL_QUESTION_RULES.get(current_differential_top, {})
    
    # Check if a must-ask question hasn't been asked yet
    for priority_q in rules.get("must_ask_first", []):
        # simple check if priority_q words are heavily present in past questions, 
        # or just exact match check if we strictly enforce the exact string
        if priority_q.lower() not in questions_already_asked_str.lower():
            return {
                "approved": False,
                "override": priority_q,
                "reason": "Higher priority clinical question not yet asked"
            }
    
    # Check if proposed question is in never_ask list
    for banned in rules.get("never_ask_here", []):
        # Check if the core concept of the banned question is in the proposed question
        # To be safe, we just check if any key nouns overlap, but for simplicity we check exact match or close
        # Here we just check if the proposed question contains words from banned
        banned_words = set([w.lower() for w in banned.replace("?","").split() if len(w) > 4])
        proposed_words = set([w.lower() for w in proposed_question.replace("?","").split()])
        if len(banned_words.intersection(proposed_words)) >= 2:
            return {
                "approved": False,
                "override": None,
                "reason": "Question clinically irrelevant for current differential"
            }
            
    # Check conditional questions
    for cond_q, valid_differentials in rules.get("ask_only_if", {}).items():
        cond_words = set([w.lower() for w in cond_q.replace("?","").split() if len(w) > 4])
        if len(cond_words.intersection(proposed_words)) >= 2:
            if current_differential_top not in valid_differentials:
                return {
                    "approved": False,
                    "override": None,
                    "reason": f"Question only relevant for {valid_differentials}"
                }
    
    return {"approved": True, "override": None, "reason": "Passed all rules"}
