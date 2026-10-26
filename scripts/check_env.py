"""Class 3 environment check: same question to OpenRouter and local Ollama.

Only base_url, key and model name differ between targets.
"""
import os, time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads OPENROUTER_API_KEY (and optional OLLAMA_BASE_URL) from .env
QUESTION = "Назви столицю України одним словом."

# Inside docker compose OLLAMA_BASE_URL points to the ollama service;
# on the host it falls back to localhost.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

TARGETS = [
    # name, base_url, key, model
    ("OpenRouter", "https://openrouter.ai/api/v1",
     os.getenv("OPENROUTER_API_KEY"), "openai/gpt-4o-mini"),
    ("Ollama", OLLAMA_BASE_URL,
     "ollama", "llama3.2:3b"),
]

for name, base_url, key, model in TARGETS:
    if not key:
        print(f"{name}: немає OPENROUTER_API_KEY у .env")
        continue
    client = OpenAI(base_url=base_url, api_key=key,
                    timeout=60, max_retries=2)
    start = time.perf_counter()
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": QUESTION}],
            temperature=0,
        )
    except Exception as e:
        print(f"{name}: помилка {type(e).__name__}: {e}")
        continue
    sec = time.perf_counter() - start
    u = r.usage
    answer = r.choices[0].message.content.strip()
    print(f"{name} | {model} | {sec:.1f} с | "
          f"токени: вхід {u.prompt_tokens}, вихід {u.completion_tokens} | {answer}")
