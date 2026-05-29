from domain.ports import AIPort


class OpenAICompatibleAdapter(AIPort):
    """Handles OpenAI, DeepSeek, Groq — all share the OpenAI API contract."""

    def __init__(self, model_id: str, api_key: str, base_url: str | None = None) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Run: uv add openai") from None

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model_id

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=2048,
        )
        return response.choices[0].message.content
