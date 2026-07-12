import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
  base_url = "https://openrouter.ai/api/v1",
  api_key = os.environ.get("OPENROUTER_API_KEY", "your-api-key")
)

# Load DDXPlus Vocabulary once at startup
# Load DDXPlus Vocabulary once at startup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
vocab_path = os.path.join(BASE_DIR, "vocab.txt")
try:
    with open(vocab_path, "r") as f:
        DDX_VOCAB = f.read()
except Exception as e:
    print(f"Failed to load DDX_VOCAB at {vocab_path}: {e}")
    DDX_VOCAB = ""

SYSTEM_PROMPT = """
You are the INTAKE AGENT for 'Predictive Patient Pathfinder', an advanced medical triage system.
Your role is strictly to extract symptoms, symptom velocity, and behavioral signals via conversational adaptive questioning.

CONTEXT:
{dynamic_context}

INSTRUCTIONS:
1. Analyze the patient's reported symptoms and any VISUAL FINDINGS from the conversation history.
2. **SYMPTOM ACKNOWLEDGEMENT**: You MUST explicitly acknowledge ALL symptoms provided by the patient (especially major injuries like fractures, trauma, or severe pain) before asking follow-up questions. Do not ignore severe physical symptoms to focus only on common ones like fever.
3. **DISCORDANCE CHECK**: If the user's verbal symptoms indicate low severity but the VISUAL FINDINGS indicate high severity, you MUST interrupt and ask a clarifying question about the visual finding to confirm urgency.
4. **VELOCITY QUESTIONS**: During triage, you MUST ask questions about symptom velocity if not already provided (e.g., "Did this start suddenly or gradually?", "Has it worsened over the last few days?").
5. **HEALTH LITERACY**: Adjust the medical complexity of your language based on the socioeconomic context provided above.
6. **SIMULATE ACOUSTIC BIOMARKERS**: Based on the transcript text style, infer potential acoustic signals (e.g., "High Fatigue").
7. **ADAPTIVE QUESTIONING**: Ask EXACTLY ONE highly discriminating follow-up question.
8. **TRIAGE COMPLETION**: Once confident you have enough information to map the patient's symptoms to DDXPlus codes (or after ~4-5 turns), conclude the triage.

OUTPUT FORMAT:
You MUST respond ONLY with a valid JSON object matching this schema. Do not include markdown formatting or outside text.
{
    "status": "question" | "complete",
    "message": "The text of your next question OR a concluding message that triage is done.",
    "simulated_acoustic_signals": ["List of inferred signals"]
}
"""

class IntakeAgent:
    """Agent 1: Extracts symptoms, velocity, and behavioral signals from conversation."""

    @staticmethod
    def chat(messages: list, dynamic_context: str = "Location unknown."):
        """Runs the conversational loop, determining if triage is complete."""
        try:
            formatted_prompt = SYSTEM_PROMPT.replace("{dynamic_context}", dynamic_context)
            full_messages = [{"role": "system", "content": formatted_prompt}] + messages
            
            response = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=full_messages,
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content
            return json.loads(response_text)
        except Exception as e:
            print(f"Error in IntakeAgent chat: {e}")
            return {
                "status": "error",
                "message": "Sorry, our AI system is currently unavailable.",
            }

    @staticmethod
    def extract_symptoms(messages: list):
        """Extracts exact DDXPlus codes from the final conversation log."""
        if not DDX_VOCAB:
            return {"symptoms": [], "verbal_severity": 0.2}
        
        convo_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages if m['role'] in ('user', 'assistant')])
        
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
                model="openai/gpt-4o-mini",
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
            print(f"Error in IntakeAgent extraction: {e}")
            return {"symptoms": [], "verbal_severity": 0.2}
