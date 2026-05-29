import os

from domain.ports import AIPort
from .registry import REGISTRY, DEFAULT_MODEL, ModelEntry


def build_ai_adapter(model_alias: str | None = None) -> AIPort:
    """
    Resolve model alias → correct adapter, injecting API key from env.
    Raises ValueError for unknown aliases or missing API keys.
    """
    alias = model_alias or DEFAULT_MODEL
    entry = _resolve(alias)
    api_key = _get_api_key(entry)
    return _instantiate(entry, api_key)


def _resolve(alias: str) -> ModelEntry:
    entry = REGISTRY.get(alias)
    if entry is None:
        available = ", ".join(sorted(REGISTRY))
        raise ValueError(f"Unknown model '{alias}'. Available: {available}")
    return entry


def _get_api_key(entry: ModelEntry) -> str | None:
    if entry.env_key is None:
        return None  # Ollama: no key needed
    key = os.getenv(entry.env_key)
    if not key:
        raise ValueError(
            f"Missing API key. Set the environment variable: {entry.env_key}"
        )
    return key


def _instantiate(entry: ModelEntry, api_key: str | None) -> AIPort:
    if entry.provider == "anthropic":
        from .anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter(entry.model_id, api_key)

    if entry.provider in ("openai", "openai_compat"):
        from .openai_adapter import OpenAICompatibleAdapter
        return OpenAICompatibleAdapter(entry.model_id, api_key, entry.base_url)

    if entry.provider == "google":
        from .google_adapter import GoogleAdapter
        return GoogleAdapter(entry.model_id, api_key)

    if entry.provider == "ollama":
        from .ollama_adapter import OllamaAdapter
        return OllamaAdapter(entry.model_id)

    raise ValueError(f"No adapter registered for provider '{entry.provider}'")
