from openai import OpenAI
import os

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key="YOUR_OPENROUTER_API_KEY")
try:
    res = client.chat.completions.create(model="meta-llama/llama-3.1-70b-instruct", messages=[{"role":"user","content":"Hi"}])
    print("Success:", res.choices[0].message.content)
except Exception as e:
    print("Error:", e)
