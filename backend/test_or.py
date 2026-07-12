from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ.get("NVIDIA_API_KEY"))
try:
    res = client.chat.completions.create(model="nvidia/llama3-chatqa-1.5-70b", messages=[{"role":"user","content":"Hi"}])
    print("OR Success:", res.choices[0].message.content)
except Exception as e:
    print("OR Error:", e)
