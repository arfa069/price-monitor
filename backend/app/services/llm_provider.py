"""LLM provider abstraction for job match analysis."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.config import settings


@dataclass(slots=True)
class MatchAnalysis:
    match_score: int
    match_reason: str
    apply_recommendation: str
    model_used: str


class LLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def analyze_match(
        self,
        resume_text: str,
        job_title: str,
        job_company: str,
        job_salary: str,
        job_location: str,
        job_experience: str,
        job_education: str,
        job_description: str,
    ) -> MatchAnalysis:
        raise NotImplementedError


def get_llm_provider() -> LLMProvider:
    provider = (settings.job_match_provider or "minimax").strip().lower()
    if provider in {"anthropic", "minimax"}:
        from app.services.llm_anthropic import AnthropicProvider

        return AnthropicProvider()
    if provider == "openai":
        from app.services.llm_openai import OpenAIProvider

        return OpenAIProvider()
    if provider == "ollama":
        from app.services.llm_ollama import OllamaProvider

        return OllamaProvider()
    raise ValueError(f"Unknown job_match_provider: {provider}")
