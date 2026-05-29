from domain.ports import AIPort


class GoogleAdapter(AIPort):
    def __init__(self, model_id: str, api_key: str) -> None:
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("Run: uv add google-generativeai") from None

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_id)

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = self._model.generate_content(full_prompt)
        return response.text
