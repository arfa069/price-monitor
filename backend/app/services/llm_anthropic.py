"""Anthropic-compatible provider for job match analysis."""

from __future__ import annotations

import json
import re

import httpx

from app.config import settings
from app.services.llm_provider import LLMProvider, MatchAnalysis


def _extract_json(content: str) -> dict:
    match = re.search(r"\{.*\}", content, flags=re.S)
    if not match:
        raise ValueError("No JSON payload found in LLM response")
    return json.loads(match.group(0))


class AnthropicProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return (settings.job_match_provider or "anthropic").strip().lower()

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
        provider_name = (settings.job_match_provider or "anthropic").strip().lower()
        if provider_name == "minimax":
            api_key = settings.minimax_api_key
            base_url = settings.minimax_base_url.rstrip("/")
            model = settings.job_match_model or "MiniMax-M2.7"
        else:
            api_key = settings.anthropic_api_key
            base_url = (settings.anthropic_base_url or "https://api.anthropic.com").rstrip("/")
            model = settings.job_match_model or "claude-3-5-sonnet-latest"

        if not api_key:
            if provider_name == "minimax":
                raise ValueError("MINIMAX_API_KEY is required")
            raise ValueError("ANTHROPIC_API_KEY is required")

        prompt = (
            "你是职位匹配分析助手。只返回JSON，不要输出多余文本。\n"
            f"简历：{resume_text}\n"
            f"职位：{job_title}\n公司：{job_company}\n薪资：{job_salary}\n地点：{job_location}\n"
            f"经验：{job_experience}\n学历：{job_education}\n描述：{job_description}\n"
            '返回字段：{"match_score":0-100,"match_reason":"中文原因","apply_recommendation":"强烈推荐/可以考虑/不太匹配"}'
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base_url}/v1/messages",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()

        content = "".join(part.get("text", "") for part in data.get("content", []))
        result = _extract_json(content)
        return MatchAnalysis(
            match_score=int(result["match_score"]),
            match_reason=str(result["match_reason"]),
            apply_recommendation=str(result["apply_recommendation"]),
            model_used=model,
        )
