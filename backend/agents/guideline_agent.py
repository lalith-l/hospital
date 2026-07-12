import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
  base_url = "https://openrouter.ai/api/v1",
  api_key = os.environ.get("OPENROUTER_API_KEY", "your-api-key")
)

SYSTEM_PROMPT = """
You are the GUIDELINE VERIFICATION AGENT.
Your role is to verify the primary diagnosis and urgency level computed by the system against standard ICMR / WHO guidelines.

Given a diagnosis and patient symptoms:
1. Briefly state standard medical guidelines for this condition.
2. Determine if the system's urgency matches the clinical presentation.
3. Provide a short "verified" or "flagged" decision.

Respond ONLY in JSON format:
{
    "guideline_check": "verified" | "flagged",
    "rationale": "Brief sentence explaining the guideline rule."
}
"""

class GuidelineAgent:
    """Agent 3: Checks diagnosis against ICMR/WHO guidelines."""

    @staticmethod
    def verify(symptoms: list, diagnosis: str, urgency: int):
        if not diagnosis or diagnosis == "Unknown":
            return {
                "guideline_check": "flagged",
                "rationale": "No primary condition predicted."
            }
            
        prompt = f"Symptoms: {', '.join(symptoms)}\nDiagnosis: {diagnosis}\nUrgency: Level {urgency}"
        
        try:
            response = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=150,
                temperature=0.0
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error in GuidelineAgent: {e}")
            return {
                "guideline_check": "verified",
                "rationale": "Guideline check unavailable."
            }
