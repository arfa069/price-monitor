"""Tests for LLM provider factory."""

import pytest


@pytest.mark.parametrize(
    ("provider_name", "expected_class_name"),
    [
        ("openai", "OpenAIProvider"),
        ("anthropic", "AnthropicProvider"),
        ("ollama", "OllamaProvider"),
    ],
)
def test_get_llm_provider_returns_expected_provider(provider_name: str, expected_class_name: str):
    """Factory should instantiate the configured provider."""
    from app.config import settings
    from app.services.llm_provider import get_llm_provider

    original_provider = settings.job_match_provider
    try:
        settings.job_match_provider = provider_name
        provider = get_llm_provider()
        assert provider.__class__.__name__ == expected_class_name
    finally:
        settings.job_match_provider = original_provider


def test_get_llm_provider_rejects_unknown_provider():
    """Factory should fail fast for unknown providers."""
    from app.config import settings
    from app.services.llm_provider import get_llm_provider

    original_provider = settings.job_match_provider
    try:
        settings.job_match_provider = "unknown-provider"
        with pytest.raises(ValueError):
            get_llm_provider()
    finally:
        settings.job_match_provider = original_provider
