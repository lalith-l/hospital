from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=os.environ.get("NVIDIA_API_KEY"))
try:
    res = client.chat.completions.create(model="meta/llama3-70b-instruct", messages=[{"role":"user","content":"Hi"}])
    print("Meta Success:", res.choices[0].message.content)
except Exception as e:
    print("Meta Error:", e)
try:
    res = client.chat.completions.create(model="nvidia/llama3-med42-70b", messages=[{"role":"user","content":"Hi"}])
    print("Med42 Success:", res.choices[0].message.content)
except Exception as e:
    print("Med42 Error:", e)
