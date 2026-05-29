from domain.ports import AIPort

_DEFAULT_HOST = "http://localhost:11434"


class OllamaAdapter(AIPort):
    """Calls a local Ollama instance — no API key required."""

    def __init__(self, model_id: str, host: str = _DEFAULT_HOST) -> None:
        try:
            import ollama
        except ImportError:
            raise ImportError("Run: uv add ollama") from None

        self._ollama = ollama
        self._model = model_id
        self._host = host

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self._ollama.Client(host=self._host).chat(
            model=self._model,
            messages=messages,
        )
        return response["message"]["content"]
