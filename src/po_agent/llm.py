"""Small provider-agnostic LLM client: Gemini (vision + text) and Groq (text).

No SDKs on purpose: two HTTP calls are easy to read, mock and debug. Responses
are cached on disk by content hash so eval runs are repeatable and cheap.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from pathlib import Path

import httpx

CACHE_DIR = Path(os.getenv("PO_CACHE_DIR", Path(__file__).resolve().parents[2] / ".cache" / "llm"))
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMError(RuntimeError):
    pass


def _gemini_models() -> list[str]:
    raw = os.getenv("GEMINI_MODELS", "gemini-3.5-flash-lite,gemini-3.8-flash,gemini-flash-latest")
    return [m.strip() for m in raw.split(",") if m.strip()]


def _cache_get(key: str) -> dict | None:
    if os.getenv("PO_NO_CACHE") == "1":
        return None
    p = CACHE_DIR / f"{key}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _cache_put(key: str, value: dict) -> None:
    if os.getenv("PO_NO_CACHE") == "1":
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.json").write_text(json.dumps(value))


def _key(*parts: bytes | str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else p.encode())
        h.update(b"\x00")
    return h.hexdigest()[:32]


def gemini_json(system: str, prompt: str, file_bytes: bytes | None = None,
                mime: str | None = None, timeout: float = 90) -> dict:
    """Ask Gemini for JSON. Tries each model in GEMINI_MODELS until one answers."""
    for model in _gemini_models():  # a cached answer needs no key and no network
        if hit := _cache_get(_key("gemini", model, system, prompt, file_bytes or b"")):
            return {**hit, "cached": True}
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise LLMError("GEMINI_API_KEY is not set")
    parts: list[dict] = [{"text": prompt}]
    if file_bytes is not None:
        parts.insert(0, {"inline_data": {"mime_type": mime, "data": base64.b64encode(file_bytes).decode()}})
    errors = []
    for model in _gemini_models():
        key = _key("gemini", model, system, prompt, file_bytes or b"")
        if hit := _cache_get(key):
            return {**hit, "cached": True}
        body = {"system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
        t0 = time.monotonic()
        try:
            r = httpx.post(GEMINI_URL.format(model=model), json=body, timeout=timeout,
                           headers={"x-goog-api-key": api_key})
        except httpx.HTTPError as e:
            errors.append(f"{model}: {type(e).__name__}")
            continue
        if r.status_code != 200:
            errors.append(f"{model}: HTTP {r.status_code}")
            continue
        data = r.json()
        try:
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError):
            errors.append(f"{model}: empty answer")
            continue
        um = data.get("usageMetadata", {})
        out = {"text": text, "provider": "gemini", "model": model,
               "input_tokens": um.get("promptTokenCount", 0),
               "output_tokens": um.get("candidatesTokenCount", 0) + um.get("thoughtsTokenCount", 0),
               "latency_ms": int((time.monotonic() - t0) * 1000)}
        _cache_put(key, out)
        return {**out, "cached": False}
    raise LLMError("all Gemini models failed: " + "; ".join(errors))


def groq_json(system: str, prompt: str, timeout: float = 60) -> dict:
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    key = _key("groq", model, system, prompt)
    if hit := _cache_get(key):
        return {**hit, "cached": True}
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise LLMError("GROQ_API_KEY is not set")
    body = {"model": model, "temperature": 0, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    t0 = time.monotonic()
    try:
        r = httpx.post(GROQ_URL, json=body, timeout=timeout, headers={"Authorization": f"Bearer {api_key}"})
    except httpx.HTTPError as e:
        raise LLMError(f"groq: {type(e).__name__}") from e
    if r.status_code != 200:
        raise LLMError(f"groq: HTTP {r.status_code}")
    data = r.json()
    um = data.get("usage", {})
    out = {"text": data["choices"][0]["message"]["content"], "provider": "groq", "model": model,
           "input_tokens": um.get("prompt_tokens", 0), "output_tokens": um.get("completion_tokens", 0),
           "latency_ms": int((time.monotonic() - t0) * 1000)}
    _cache_put(key, out)
    return {**out, "cached": False}
