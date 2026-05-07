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
    "Gemini":     "gemini",
    "Claude":     "claude",
    "OpenAI":     "openai",
    "Ollama":     "ollama",
    "Cloudflare": "custom_url",
    "Custom URL": "custom_url",
}

DEFAULT_MODELS: dict[str, str] = {
    "gemini":     "gemini-2.5-flash",
    "claude":     "claude-opus-4-5",
    "openai":     "gpt-4o",
    "ollama":     "llava:13b",
    "custom_url": "",
}

# Known models per provider shown in the dropdown
# Gemini models verified against ai.google.dev/gemini-api/docs/models (May 2026)
PROVIDER_MODELS: dict[str, list[str]] = {
    "gemini": [
        # Free tier (recommended)
        "gemini-2.5-flash",          # best free tier, multimodal
        "gemini-2.5-flash-lite",     # fastest, budget friendly
        "gemini-3-flash-preview",    # latest preview, free tier
        "gemini-3.1-flash-lite-preview",
        # Paid
        "gemini-2.5-pro",            # advanced reasoning, billing required
        "gemini-3.1-pro-preview",    # billing required
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
        "llava:13b",       # 8GB — best quality vision, recommended
        "gemma3:12b",      # 7GB — Google Gemma 3 multimodal, free
        "llava:7b",        # 4GB — lighter option
        "llava:34b",       # 20GB — highest quality, needs lots of RAM
        "llava-llama3",    # 5GB — good balance
        "moondream",       # 1.7GB — fastest, lower quality
        "Other (type below)",
    ],
    "custom_url": [
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
        "kpi_worker": _classify_kpi_worker,
        "gemini":     _classify_gemini,
        "claude":     _classify_claude,
        "openai":     _classify_openai,
        "ollama":     _classify_ollama,
        "custom_url": _classify_custom_url,
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
            "User-Agent":    "KPI-Assistant/1.0 (Windows)",
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
        headers={
            "Content-Type": "application/json",
            "User-Agent": "KPI-Assistant/1.0 (Windows)",
        },
    )
    # 300s timeout — local models can take 30-60s to load into RAM on first call
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as e:
        if "timed out" in str(e).lower():
            raise RuntimeError(
                f"Ollama timed out after 5 minutes. The model '{model}' may still be "
                f"loading into RAM. Try again in a moment, or use a smaller model like llava:7b."
            ) from e
        raise
    return data["response"]


# ── KPI Worker (default — baked-in token, no user config needed) ─────────────
def _classify_kpi_worker(image_path: str, instructions: str,
                          api_key: str, model: str) -> str:
    """
    Sends to the official KPI Assistant Cloudflare Worker.
    Auth token is baked into the EXE at build time — user needs no API key.
    """
    from app.secrets import KPI_WORKER_URL, WORKER_TOKEN
    import io

    with Image.open(image_path) as raw:
        img = raw.copy().convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()

    payload = json.dumps({
        "image_base64": b64,
        "prompt":       instructions,
        "model":        "",
    }).encode()

    headers = {
        "Content-Type":  "application/json",
        "X-Auth-Token":  WORKER_TOKEN,
        "User-Agent":    "KPI-Assistant/1.0 (Windows)",
    }

    req = urllib.request.Request(KPI_WORKER_URL, data=payload, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 401:
            raise RuntimeError("KPI Worker rejected the request — token mismatch. Please update the app.") from e
        raise RuntimeError(f"KPI Worker error {e.code}: {body}") from e

    return data.get("response", "")


# ── Custom URL (Cloudflare Worker or any compatible endpoint) ─────────────────
def _classify_custom_url(image_path: str, instructions: str,
                          api_key: str, model: str) -> str:
    """
    POST to any custom endpoint that accepts:
      { image_base64: str, prompt: str, model: str }
    and returns:
      { response: str }

    API key field format:
      - Just the URL: https://your-worker.workers.dev
      - URL with auth: https://your-worker.workers.dev|your-auth-token
    """
    import io

    # Parse URL and optional auth token from api_key field
    if "|" in api_key:
        url, auth_token = api_key.split("|", 1)
    else:
        url, auth_token = api_key.strip(), ""

    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        raise RuntimeError(
            "Custom URL provider requires a valid URL in the API Key field.\n"
            "Format: https://your-endpoint.com  or  https://your-endpoint.com|auth-token"
        )

    with Image.open(image_path) as raw:
        img = raw.copy().convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()

    payload = json.dumps({
        "image_base64": b64,
        "prompt":       instructions,
        "model":        model or "",
    }).encode()

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "KPI-Assistant/1.0 (Windows)",
    }
    if auth_token:
        headers["X-Auth-Token"] = auth_token

    req = urllib.request.Request(url, data=payload, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Custom endpoint returned {e.code}: {body}") from e

    if "response" not in data:
        raise RuntimeError(f"Custom endpoint response missing 'response' key. Got: {data}")

    return data["response"]
