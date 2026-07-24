"""Local <-> Cloud model configuration.

Both paths speak the exact same Ollama /api/chat shape — only the host and
auth differ. Defaults come from environment variables so nothing here is
hardcoded per-machine; every field can also be overridden per-request (see
ChatRequest.provider in schemas.py) so the frontend can flip between local
and cloud without restarting the server.

Env vars:
  NUTRIMATE_MODEL_PROVIDER   "local" | "cloud"   (default: "local")
  OLLAMA_LOCAL_HOST          default: http://localhost:11434
  OLLAMA_LOCAL_MODEL         default: gemma4:e4b      (small, laptop-friendly)
  OLLAMA_CLOUD_HOST          default: https://ollama.com
  OLLAMA_CLOUD_MODEL         default: gemma4:31b-cloud
  OLLAMA_API_KEY             required for cloud; create one at
                             https://ollama.com/settings/keys
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    host: str
    model: str
    api_key: str | None


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


DEFAULT_PROVIDER = _get("NUTRIMATE_MODEL_PROVIDER", "local").strip().lower()

LOCAL_HOST = _get("OLLAMA_LOCAL_HOST", "http://localhost:11434").rstrip("/")
LOCAL_MODEL = _get("OLLAMA_LOCAL_MODEL", "gemma4:e4b")

CLOUD_HOST = _get("OLLAMA_CLOUD_HOST", "https://ollama.com").rstrip("/")
CLOUD_MODEL = _get("OLLAMA_CLOUD_MODEL", "gemma4:31b-cloud")

API_KEY = os.environ.get("OLLAMA_API_KEY")  # None if unset — cloud calls will fail clearly


def resolve(provider: str | None) -> ProviderConfig:
    """Resolve a provider name ('local' | 'cloud' | None) to concrete host/model/key.

    None falls back to DEFAULT_PROVIDER, so every caller can just say
    `resolve(request.provider)` without worrying about the unset case.
    """
    p = (provider or DEFAULT_PROVIDER).strip().lower()
    if p not in ("local", "cloud"):
        raise ValueError(f"Unknown model provider '{p}' — expected 'local' or 'cloud'")

    if p == "local":
        return ProviderConfig(provider="local", host=LOCAL_HOST, model=LOCAL_MODEL, api_key=None)

    return ProviderConfig(provider="cloud", host=CLOUD_HOST, model=CLOUD_MODEL, api_key=API_KEY)


def cloud_is_configured() -> bool:
    return bool(API_KEY)
