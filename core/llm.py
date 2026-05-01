"""Thin wrapper around the local Ollama HTTP API.

We deliberately avoid heavy SDK dependencies — agents call `ollama_chat`
directly. Every call is logged via core.logger so the full agent trace
appears in logs/run.log.
"""
from __future__ import annotations

import os
import time
from typing import Optional

import requests

from core.logger import get_logger

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3:8b")
DEFAULT_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))

_logger = get_logger("llm")


class OllamaError(RuntimeError):
    """Raised when the Ollama server returns an error or is unreachable."""


def ollama_chat(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    agent_name: str = "unknown",
) -> str:
    """Send a chat-style request to the local Ollama server.

    Args:
        system_prompt: Persona/constraints injected as the system role.
        user_prompt: The user-side message (already-formatted context + task).
        model: Ollama model tag (default `llama3:8b`).
        temperature: Sampling temperature. Lower = more deterministic.
        agent_name: Used only for logging — identifies which agent made the call.

    Returns:
        The assistant's response content as a string.

    Raises:
        OllamaError: If the server is unreachable or returns a non-200.
    """
    url = f"{OLLAMA_URL}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }

    start = time.perf_counter()
    _logger.info(
        "[%s] -> ollama_chat model=%s temp=%.2f prompt_chars=%d",
        agent_name, model, temperature, len(user_prompt),
    )

    try:
        response = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
    except requests.exceptions.RequestException as exc:
        _logger.error("[%s] Ollama request failed: %s", agent_name, exc)
        raise OllamaError(
            f"Could not reach Ollama at {OLLAMA_URL}. Is `ollama serve` running?"
        ) from exc

    if response.status_code != 200:
        _logger.error(
            "[%s] Ollama %d: %s", agent_name, response.status_code, response.text[:200]
        )
        raise OllamaError(
            f"Ollama returned {response.status_code}: {response.text[:200]}"
        )

    data = response.json()
    content: Optional[str] = (data.get("message") or {}).get("content")
    if not content:
        raise OllamaError(f"Ollama response missing 'message.content': {data}")

    elapsed = time.perf_counter() - start
    _logger.info(
        "[%s] <- ollama_chat ok elapsed=%.2fs response_chars=%d",
        agent_name, elapsed, len(content),
    )
    return content.strip()
