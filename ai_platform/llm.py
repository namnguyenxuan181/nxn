"""
LLM abstraction — priority: DeepSeek → Anthropic → Ollama → error message.
Set DEEPSEEK_API_KEY to use DeepSeek (recommended).
"""

import json
import os
from typing import Dict, Generator, List, Optional

import requests

_DEEPSEEK_MODEL  = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
_OLLAMA_URL      = os.environ.get("OLLAMA_URL", "http://localhost:11434")
_OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "llama3.2")

_NO_LLM = (
    "Không có LLM khả dụng. "
    "Hãy đặt DEEPSEEK_API_KEY hoặc cài Ollama (ollama pull llama3.2)."
)


def _ollama_running() -> bool:
    try:
        return requests.get(f"{_OLLAMA_URL}/api/tags", timeout=2).status_code == 200
    except Exception:
        return False


def stream_response(system: str, messages: List[Dict]) -> Generator[str, None, None]:
    """Stream text tokens. DeepSeek → Anthropic → Ollama → error message."""
    if os.environ.get("DEEPSEEK_API_KEY"):
        yield from _deepseek_stream(system, messages)
    elif os.environ.get("ANTHROPIC_API_KEY"):
        yield from _anthropic_stream(system, messages)
    elif _ollama_running():
        yield from _ollama_stream(system, messages)
    else:
        yield _NO_LLM


def complete(messages: List[Dict]) -> str:
    """Single-turn completion. DeepSeek → Anthropic → Ollama → error message."""
    if os.environ.get("DEEPSEEK_API_KEY"):
        return _deepseek_complete(messages)
    elif os.environ.get("ANTHROPIC_API_KEY"):
        return _anthropic_complete(messages)
    elif _ollama_running():
        return _ollama_complete(messages)
    else:
        return _NO_LLM


# ── DeepSeek (OpenAI-compatible API) ─────────────────────────────────────────

def _deepseek_client():
    from openai import OpenAI
    return OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
    )


def _build_messages(system: Optional[str], messages: List[Dict]) -> List[Dict]:
    if system:
        return [{"role": "system", "content": system}] + list(messages)
    return list(messages)


def _deepseek_stream(system: str, messages: List[Dict]) -> Generator[str, None, None]:
    try:
        client = _deepseek_client()
        stream = client.chat.completions.create(
            model=_DEEPSEEK_MODEL,
            messages=_build_messages(system, messages),
            max_tokens=2048,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        yield f"Lỗi DeepSeek: {e}"


def _deepseek_complete(messages: List[Dict]) -> str:
    try:
        client = _deepseek_client()
        resp = client.chat.completions.create(
            model=_DEEPSEEK_MODEL,
            messages=messages,
            max_tokens=2048,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Lỗi DeepSeek: {e}"


# ── Anthropic ─────────────────────────────────────────────────────────────────

def _anthropic_stream(system: str, messages: List[Dict]) -> Generator[str, None, None]:
    import anthropic
    client = anthropic.Anthropic()
    with client.messages.stream(
        model=_ANTHROPIC_MODEL,
        max_tokens=2048,
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
        max_tokens=2048,
        messages=messages,
    )
    return response.content[0].text


# ── Ollama ────────────────────────────────────────────────────────────────────

def _ollama_stream(system: str, messages: List[Dict]) -> Generator[str, None, None]:
    try:
        resp = requests.post(
            f"{_OLLAMA_URL}/api/chat",
            json={
                "model": _OLLAMA_MODEL,
                "messages": _build_messages(system, messages),
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
                "messages": _build_messages(None, messages),
                "stream": False,
            },
            timeout=120,
        )
        return resp.json()["message"]["content"]
    except Exception as e:
        return f"Lỗi Ollama: {e}"
