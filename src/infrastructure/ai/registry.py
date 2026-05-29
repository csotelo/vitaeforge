from dataclasses import dataclass


@dataclass(frozen=True)
class ModelEntry:
    provider: str
    model_id: str
    base_url: str | None = None      # only for openai-compatible endpoints
    env_key: str | None = None       # env var that holds the API key


# alias → ModelEntry
# Add new models here without touching any other file (Open/Closed)
REGISTRY: dict[str, ModelEntry] = {
    # --- Anthropic ---
    "claude-haiku":   ModelEntry("anthropic", "claude-haiku-4-5-20251001",    env_key="ANTHROPIC_API_KEY"),
    "claude-sonnet":  ModelEntry("anthropic", "claude-sonnet-4-6",            env_key="ANTHROPIC_API_KEY"),
    "claude-opus":    ModelEntry("anthropic", "claude-opus-4-7",              env_key="ANTHROPIC_API_KEY"),

    # --- OpenAI ---
    "gpt-4o-mini":    ModelEntry("openai", "gpt-4o-mini",                     env_key="OPENAI_API_KEY"),
    "gpt-4o":         ModelEntry("openai", "gpt-4o",                          env_key="OPENAI_API_KEY"),

    # --- DeepSeek (OpenAI-compatible, free tier) ---
    "deepseek-chat":      ModelEntry("openai_compat", "deepseek-chat",
                                     base_url="https://api.deepseek.com",     env_key="DEEPSEEK_API_KEY"),
    "deepseek-reasoner":  ModelEntry("openai_compat", "deepseek-reasoner",
                                     base_url="https://api.deepseek.com",     env_key="DEEPSEEK_API_KEY"),

    # --- Groq (OpenAI-compatible, free tier) ---
    "groq-llama":    ModelEntry("openai_compat", "llama-3.3-70b-versatile",
                                base_url="https://api.groq.com/openai/v1",    env_key="GROQ_API_KEY"),
    "groq-mixtral":  ModelEntry("openai_compat", "mixtral-8x7b-32768",
                                base_url="https://api.groq.com/openai/v1",    env_key="GROQ_API_KEY"),

    # --- Google Gemini ---
    "gemini-flash":  ModelEntry("google", "gemini-2.0-flash",                 env_key="GOOGLE_API_KEY"),
    "gemini-pro":    ModelEntry("google", "gemini-1.5-pro",                   env_key="GOOGLE_API_KEY"),

    # --- Ollama (local, no key needed) ---
    "ollama-llama3": ModelEntry("ollama", "llama3"),
    "ollama-qwen":   ModelEntry("ollama", "qwen2.5"),
    "ollama-mistral":ModelEntry("ollama", "mistral"),
}


# Priority order for auto-detection — first model whose key is present wins
_PRIORITY = [
    "gpt-4o-mini",
    "groq-llama",
    "gemini-flash",
    "claude-haiku",
    "deepseek-chat",
    "ollama-llama3",
]

def _detect_default() -> str:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    # Explicit config always wins
    if configured := os.environ.get("VITAEFORGE_MODEL"):
        return configured
    # Fallback: first model whose API key is present
    for alias in _PRIORITY:
        entry = REGISTRY.get(alias)
        if entry and (entry.env_key is None or os.environ.get(entry.env_key)):
            return alias
    return _PRIORITY[0]

DEFAULT_MODEL = _detect_default()
