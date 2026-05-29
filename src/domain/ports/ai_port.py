from abc import ABC, abstractmethod


class AIPort(ABC):
    """Domain port: single contract all AI adapters must satisfy."""

    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Send a prompt, return the model's text response."""
        ...
