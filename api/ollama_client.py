"""Thin wrapper around Ollama's /api/chat — same shape for local and cloud.

Docs: https://docs.ollama.com/api  /  https://docs.ollama.com/cloud
"""

import httpx

from config import ProviderConfig


class OllamaError(RuntimeError):
    """Raised for anything that stops us from getting a chat response —
    unreachable local daemon, missing cloud API key, HTTP error, etc. Always
    carries a message safe to show directly to a user."""


def chat(cfg: ProviderConfig, messages: list[dict], tools: list[dict] | None = None) -> dict:
    if cfg.provider == "cloud" and not cfg.api_key:
        raise OllamaError(
            "Cloud model selected, but no OLLAMA_API_KEY is configured. "
            "Create one at https://ollama.com/settings/keys and set it as an "
            "environment variable, or switch to the local model."
        )

    headers = {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}
    payload = {"model": cfg.model, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools

    try:
        resp = httpx.post(f"{cfg.host}/api/chat", json=payload, headers=headers, timeout=120)
    except httpx.ConnectError as e:
        if cfg.provider == "local":
            raise OllamaError(
                f"Couldn't reach a local Ollama server at {cfg.host}. "
                "Is `ollama serve` running, and have you pulled the model "
                f"('ollama pull {cfg.model}')?"
            ) from e
        raise OllamaError(f"Couldn't reach Ollama Cloud at {cfg.host}: {e}") from e
    except httpx.TimeoutException as e:
        raise OllamaError(f"Ollama ({cfg.provider}, model={cfg.model}) timed out.") from e

    if resp.status_code == 401:
        raise OllamaError("Ollama Cloud rejected the API key (401). Check OLLAMA_API_KEY.")
    if resp.status_code == 404:
        raise OllamaError(
            f"Model '{cfg.model}' isn't available on {cfg.provider}. "
            f"{'Pull it with `ollama pull ' + cfg.model + '`.' if cfg.provider == 'local' else ''}"
        )
    if resp.status_code >= 400:
        raise OllamaError(f"Ollama returned {resp.status_code}: {resp.text[:300]}")

    return resp.json()
