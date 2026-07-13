import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
  base_url = "https://api.groq.com/openai/v1",
  api_key = os.environ.get("GROQ_API_KEY")
)

try:
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "system", "content": "Return a JSON object with key 'hello' and value 'world'"}, {"role": "user", "content": "hi"}],
        response_format={"type": "json_object"}
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
