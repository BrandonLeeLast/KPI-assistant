"""
AI provider abstraction.

Each provider implements classify(image_path, instructions, api_key, model) -> str
returning the raw text response. The processor calls get_provider() to resolve
whichever the user has configured, then calls classify() on it.

Adding a new provider:
  1. Create a function _classify_<name>(...)
  2. Register it in PROVIDERS dict below.
"""

from __future__ import annotations
import base64
import urllib.request
import urllib.error
import json
from PIL import Image


# ── Provider registry ─────────────────────────────────────────────────────────
PROVIDERS: dict[str, str] = {
    "Gemini":  "gemini",
    "Claude":  "claude",
    "OpenAI":  "openai",
    "Ollama":  "ollama",
}

DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-2.0-flash",
    "claude": "claude-opus-4-5",
    "openai": "gpt-4o",
    "ollama": "llava",
}

# Known models per provider shown in the dropdown
PROVIDER_MODELS: dict[str, list[str]] = {
    "gemini": [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "Other (type below)",
    ],
    "claude": [
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
        "claude-opus-4-7",
        "Other (type below)",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "Other (type below)",
    ],
    "ollama": [
        "llava",
        "llava:13b",
        "llava:34b",
        "llava-llama3",
        "moondream",
        "Other (type below)",
    ],
}


def classify(image_path: str, instructions: str, provider: str,
             api_key: str, model: str) -> str:
    """
    Route to the correct provider and return the raw classification text.
    Raises RuntimeError with a user-friendly message on failure.
    """
    fn = {
        "gemini": _classify_gemini,
        "claude": _classify_claude,
        "openai": _classify_openai,
        "ollama": _classify_ollama,
    }.get(provider.lower())

    if fn is None:
        raise RuntimeError(f"Unknown provider: '{provider}'")

    return fn(image_path, instructions, api_key, model)


# ── Gemini ────────────────────────────────────────────────────────────────────
def _classify_gemini(image_path: str, instructions: str,
                     api_key: str, model: str) -> str:
    from google import genai

    client = genai.Client(api_key=api_key)
    with Image.open(image_path) as raw:
        img = raw.copy()

    response = client.models.generate_content(
        model=model,
        contents=[instructions, img],
    )
    return response.text


# ── Claude (Anthropic) ────────────────────────────────────────────────────────
def _classify_claude(image_path: str, instructions: str,
                     api_key: str, model: str) -> str:
    import anthropic

    with Image.open(image_path) as raw:
        img = raw.copy().convert("RGB")

    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": instructions},
            ],
        }],
    )
    return message.content[0].text


# ── OpenAI ────────────────────────────────────────────────────────────────────
def _classify_openai(image_path: str, instructions: str,
                     api_key: str, model: str) -> str:
    import io
    with Image.open(image_path) as raw:
        img = raw.copy().convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()

    payload = json.dumps({
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": instructions},
            ],
        }],
        "max_tokens": 1024,
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


# ── Ollama (local) ────────────────────────────────────────────────────────────
def _classify_ollama(image_path: str, instructions: str,
                     api_key: str, model: str) -> str:
    """
    api_key is reused as the Ollama base URL (default: http://localhost:11434).
    Leave API key blank or set to the URL.
    """
    import io
    base_url = api_key.strip().rstrip("/") if api_key.strip().startswith("http") \
               else "http://localhost:11434"

    with Image.open(image_path) as raw:
        img = raw.copy().convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()

    payload = json.dumps({
        "model":  model,
        "prompt": instructions,
        "images": [b64],
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["response"]
