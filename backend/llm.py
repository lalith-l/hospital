import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI(
  base_url = "https://api.groq.com/openai/v1",
  api_key = os.environ.get("GROQ_API_KEY", "your-api-key")
)

# Load DDXPlus Vocabulary once at startup
try:
    with open("ddxplus_data/vocab.txt", "r") as f:
        DDX_VOCAB = f.read()
except:
    DDX_VOCAB = ""

SYSTEM_PROMPT = """
You are the AI engine for 'Predictive Patient Pathfinder', an advanced medical triage system.
Your core mechanism mimics a Graph Attention Network (GAT) for adaptive medical questioning.

CONTEXT:
{dynamic_context}

INSTRUCTIONS:
1. Analyze the patient's reported symptoms and any VISUAL FINDINGS from the conversation history.
2. **SYMPTOM ACKNOWLEDGEMENT**: You MUST explicitly acknowledge ALL symptoms provided by the patient (especially major injuries like fractures, trauma, or severe pain) before asking follow-up questions. Do not ignore severe physical symptoms to focus only on common ones like fever.
3. **DISCORDANCE CHECK**: If the user's verbal symptoms indicate low severity but the VISUAL FINDINGS indicate high severity, you MUST interrupt and ask a clarifying question about the visual finding to confirm urgency.
4. **VELOCITY QUESTIONS**: During triage, you MUST ask questions about symptom velocity if not already provided (e.g., "Did this start suddenly or gradually?", "Has it worsened over the last few days?"). This is critical for urgency calculation.
4. **HEALTH LITERACY**: Adjust the medical complexity of your language based on the socioeconomic context provided above.
5. **SIMULATE ACOUSTIC BIOMARKERS**: Based on the transcript text style, infer potential acoustic signals (e.g., "High Fatigue").
6. **DIFFERENTIAL DIAGNOSIS**: Internally rank the possible conditions based on symptoms and the geographical prior provided in context.
7. **ADAPTIVE QUESTIONING (Entropy Reduction)**: If you are not highly confident, ask EXACTLY ONE highly discriminating follow-up question.
8. **TRIAGE COMPLETION**: Once confident (or after ~4-5 turns), conclude the triage. Assign an urgency level: 1 (Critical), 2 (Urgent), 3 (Routine).

OUTPUT FORMAT:
You MUST respond ONLY with a valid JSON object matching this schema. Do not include markdown formatting or outside text.
{
    "status": "question" | "complete",
    "message": "The text of your next question OR the summary of the final triage.",
    "condition": "The predicted condition (null if status is question)",
    "urgency": 1 | 2 | 3 | null,
    "simulated_acoustic_signals": ["List of inferred signals"],
    "disease_probabilities": [
        {"name": "Dengue", "score": 0.45},
        {"name": "Typhoid", "score": 0.2}
    ]
}
"""

def analyze_image(base64_image: str):
    try:
        response = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "You are a medical visual analyzer. Output a JSON object with 'visual_severity' (1, 2, or 3, where 1 is critical) and 'key_findings' (a short string describing visible signs like rash, swelling, etc.). Do not include markdown."},
                        {"type": "image_url", "image_url": {"url": base64_image}}
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=300
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error calling vision model: {e}")
        return {"visual_severity": 3, "key_findings": "Error analyzing image."}

def extract_symptoms(messages: list) -> list:
    if not DDX_VOCAB:
        return []
    
    # Extract only user and assistant messages for symptom extraction
    convo_text = "\\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages if m['role'] in ('user', 'assistant')])
    
    prompt = f"""Given this patient conversation, extract all reported symptoms.
Match them to the exact symptom keys from the following DDXPlus vocabulary list.
Vocabulary Mapping (Key: Symptom Description):
{DDX_VOCAB}

If a symptom is described but not in the vocabulary, find the closest match.
Return ONLY a valid JSON object with two keys:
1. "symptoms": A JSON array of matched symptom keys (e.g., ["E_91", "E_53"]). If none match, return an empty array [].
2. "verbal_severity": A float between 0.0 and 1.0 representing the patient's claimed severity of their symptoms (0.0 = completely fine, 1.0 = excruciating pain / life-threatening).

Do NOT wrap in markdown blocks, just the JSON object.

Conversation:
{convo_text}"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=150,
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
        return json.loads(content)
    except Exception as e:
        print(f"Error extracting symptoms: {e}")
        return {"symptoms": [], "verbal_severity": 0.2}

def generate_triage_response(messages: list, dynamic_context: str = "Location unknown."):
    try:
        formatted_prompt = SYSTEM_PROMPT.replace("{dynamic_context}", dynamic_context)
        full_messages = [{"role": "system", "content": formatted_prompt}] + messages
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=full_messages,
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )
        
        response_text = response.choices[0].message.content
        return json.loads(response_text)
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return {
            "status": "error",
            "message": "Sorry, our AI system is currently unavailable.",
            "error_details": str(e)
        }
