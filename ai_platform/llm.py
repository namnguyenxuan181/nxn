"""
LLM abstraction — uses Anthropic if ANTHROPIC_API_KEY is set,
otherwise falls back to Ollama running at OLLAMA_URL (default: localhost:11434).
"""

import json
import os
from typing import Dict, Generator, List, Optional

import requests

_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

_NO_LLM = (
    "Không có LLM khả dụng. "
    "Hãy cài Ollama (ollama pull llama3.2) hoặc đặt ANTHROPIC_API_KEY."
)


def _ollama_running() -> bool:
    try:
        return requests.get(f"{_OLLAMA_URL}/api/tags", timeout=2).status_code == 200
    except Exception:
        return False


def stream_response(system: str, messages: List[Dict]) -> Generator[str, None, None]:
    """Stream text tokens. Anthropic → Ollama → error message."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        yield from _anthropic_stream(system, messages)
    elif _ollama_running():
        yield from _ollama_stream(system, messages)
    else:
        yield _NO_LLM


def complete(messages: List[Dict]) -> str:
    """Single-turn completion. Anthropic → Ollama → error message."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _anthropic_complete(messages)
    elif _ollama_running():
        return _ollama_complete(messages)
    else:
        return _NO_LLM


# ── Anthropic ─────────────────────────────────────────────────────────────────

def _anthropic_stream(system: str, messages: List[Dict]) -> Generator[str, None, None]:
    import anthropic
    client = anthropic.Anthropic()
    with client.messages.stream(
        model=_ANTHROPIC_MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text


def _anthropic_complete(messages: List[Dict]) -> str:
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=_ANTHROPIC_MODEL,
        max_tokens=1024,
        messages=messages,
    )
    return response.content[0].text


# ── Ollama ────────────────────────────────────────────────────────────────────

def _with_system(system: Optional[str], messages: List[Dict]) -> List[Dict]:
    if system:
        return [{"role": "system", "content": system}] + list(messages)
    return list(messages)


def _ollama_stream(system: str, messages: List[Dict]) -> Generator[str, None, None]:
    try:
        resp = requests.post(
            f"{_OLLAMA_URL}/api/chat",
            json={
                "model": _OLLAMA_MODEL,
                "messages": _with_system(system, messages),
                "stream": True,
            },
            stream=True,
            timeout=120,
        )
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content
            if chunk.get("done"):
                break
    except Exception as e:
        yield f"Lỗi Ollama: {e}"


def _ollama_complete(messages: List[Dict]) -> str:
    try:
        resp = requests.post(
            f"{_OLLAMA_URL}/api/chat",
            json={
                "model": _OLLAMA_MODEL,
                "messages": _with_system(None, messages),
                "stream": False,
            },
            timeout=120,
        )
        return resp.json()["message"]["content"]
    except Exception as e:
        return f"Lỗi Ollama: {e}"
