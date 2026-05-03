"""Ollama provider for job match analysis."""

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


class OllamaProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "ollama"

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
        model = settings.job_match_model or "qwen2.5:7b"
        prompt = (
            "你是职位匹配分析助手。只返回JSON，不要输出多余文本。\n"
            f"简历：{resume_text}\n"
            f"职位：{job_title}\n公司：{job_company}\n薪资：{job_salary}\n地点：{job_location}\n"
            f"经验：{job_experience}\n学历：{job_education}\n描述：{job_description}\n"
            '返回字段：{"match_score":0-100,"match_reason":"中文原因","apply_recommendation":"强烈推荐/可以考虑/不太匹配"}'
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()

        content = data.get("message", {}).get("content", "")
        result = _extract_json(content)
        return MatchAnalysis(
            match_score=int(result["match_score"]),
            match_reason=str(result["match_reason"]),
            apply_recommendation=str(result["apply_recommendation"]),
            model_used=model,
        )
