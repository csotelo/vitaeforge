import os
import unittest
from unittest.mock import MagicMock, patch

from domain.ports import AIPort
from infrastructure.ai.registry import REGISTRY, DEFAULT_MODEL
from infrastructure.ai.factory import build_ai_adapter


class TestAIPort(unittest.TestCase):
    """Port contract: any adapter must satisfy AIPort."""

    def test_port_is_abstract(self):
        with self.assertRaises(TypeError):
            AIPort()  # cannot instantiate abstract class

    def test_concrete_adapter_satisfies_port(self):
        class FakeAdapter(AIPort):
            def complete(self, prompt, *, system=None):
                return "ok"

        adapter = FakeAdapter()
        self.assertIsInstance(adapter, AIPort)
        self.assertEqual(adapter.complete("hi"), "ok")


class TestRegistry(unittest.TestCase):
    """Registry contains all expected providers and a sane default."""

    def test_default_model_exists(self):
        self.assertIn(DEFAULT_MODEL, REGISTRY)

    def test_all_providers_represented(self):
        providers = {e.provider for e in REGISTRY.values()}
        self.assertIn("anthropic", providers)
        self.assertIn("openai", providers)
        self.assertIn("openai_compat", providers)
        self.assertIn("google", providers)
        self.assertIn("ollama", providers)

    def test_openai_compat_entries_have_base_url(self):
        for alias, entry in REGISTRY.items():
            if entry.provider == "openai_compat":
                self.assertIsNotNone(entry.base_url, f"{alias} missing base_url")

    def test_ollama_entries_have_no_env_key(self):
        for alias, entry in REGISTRY.items():
            if entry.provider == "ollama":
                self.assertIsNone(entry.env_key, f"{alias} should need no API key")


class TestFactory(unittest.TestCase):
    """Factory resolves aliases and injects keys correctly."""

    def test_unknown_alias_raises(self):
        with self.assertRaises(ValueError, msg="should reject unknown alias"):
            build_ai_adapter("nonexistent-model-xyz")

    def test_missing_api_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            # deepseek-chat requires DEEPSEEK_API_KEY
            os.environ.pop("DEEPSEEK_API_KEY", None)
            with self.assertRaises(ValueError, msg="should reject missing key"):
                build_ai_adapter("deepseek-chat")

    def test_builds_anthropic_adapter(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("infrastructure.ai.anthropic_adapter.AnthropicAdapter.__init__", return_value=None):
                adapter = build_ai_adapter("claude-haiku")
                from infrastructure.ai.anthropic_adapter import AnthropicAdapter
                self.assertIsInstance(adapter, AnthropicAdapter)

    def test_builds_openai_adapter(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("infrastructure.ai.openai_adapter.OpenAICompatibleAdapter.__init__", return_value=None):
                adapter = build_ai_adapter("gpt-4o-mini")
                from infrastructure.ai.openai_adapter import OpenAICompatibleAdapter
                self.assertIsInstance(adapter, OpenAICompatibleAdapter)

    def test_builds_deepseek_via_openai_compat(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            with patch("infrastructure.ai.openai_adapter.OpenAICompatibleAdapter.__init__", return_value=None):
                adapter = build_ai_adapter("deepseek-chat")
                from infrastructure.ai.openai_adapter import OpenAICompatibleAdapter
                self.assertIsInstance(adapter, OpenAICompatibleAdapter)

    def test_builds_google_adapter(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            with patch("infrastructure.ai.google_adapter.GoogleAdapter.__init__", return_value=None):
                adapter = build_ai_adapter("gemini-flash")
                from infrastructure.ai.google_adapter import GoogleAdapter
                self.assertIsInstance(adapter, GoogleAdapter)

    def test_builds_ollama_adapter_without_key(self):
        with patch("infrastructure.ai.ollama_adapter.OllamaAdapter.__init__", return_value=None):
            adapter = build_ai_adapter("ollama-llama3")
            from infrastructure.ai.ollama_adapter import OllamaAdapter
            self.assertIsInstance(adapter, OllamaAdapter)

    def test_default_model_used_when_no_alias(self):
        """build_ai_adapter() with no arg falls back to DEFAULT_MODEL."""
        entry = REGISTRY[DEFAULT_MODEL]
        env_key = entry.env_key
        with patch.dict(os.environ, {env_key: "test-key"}):
            with patch("infrastructure.ai.openai_adapter.OpenAICompatibleAdapter.__init__", return_value=None):
                adapter = build_ai_adapter()
                from infrastructure.ai.openai_adapter import OpenAICompatibleAdapter
                self.assertIsInstance(adapter, OpenAICompatibleAdapter)
