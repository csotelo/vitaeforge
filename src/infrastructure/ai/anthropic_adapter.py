from domain.ports import AIPort


class AnthropicAdapter(AIPort):
    def __init__(self, model_id: str, api_key: str) -> None:
        try:
            import anthropic as sdk
        except ImportError:
            raise ImportError("Run: uv add anthropic") from None

        self._client = sdk.Anthropic(api_key=api_key)
        self._model = model_id

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        kwargs: dict = {
            "model": self._model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self._client.messages.create(**kwargs)
        return response.content[0].text
