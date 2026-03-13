import httpx
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.0.5:11434")
MODEL = "llama3.1:8b"
TIMEOUT = 60.0


async def call_ollama(system_prompt: str, user_message: str) -> str:
    payload = {
        "model": MODEL,
        "prompt": f"{system_prompt}\n\nPlayer: {user_message}\n\nDungeon Master:",
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "num_ctx": 8192,
            "temperature": 0.8,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
    except httpx.TimeoutException:
        return "The Dungeon Master ponders in silence… (Ollama timed out — is the PC on?)"
    except httpx.HTTPStatusError as e:
        return f"The Dungeon Master falters… (Ollama error {e.response.status_code})"
    except Exception as e:
        return f"The Dungeon Master is lost in thought… (Connection error: {type(e).__name__})"
