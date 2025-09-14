import requests
from config import Config

def call_groq(prompt, max_tokens=800):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.1-8b-instant",   # Groq ka free + powerful model
        "messages": [
            {"role": "system", "content": "You are a meeting notes generator."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens
    }
    r = requests.post(url, json=data, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def call_llm(prompt, **kwargs):
    return call_groq(prompt, **kwargs)
