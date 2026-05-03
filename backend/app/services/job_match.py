"""Resume-job match analysis service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.job import Job, JobSearchConfig
from app.models.job_match import MatchResult, UserResume
from app.models.user import User
from app.services.llm_provider import MatchAnalysis, get_llm_provider
from app.services.notification import send_feishu_notification


def should_notify_match(score: int) -> bool:
    """Whether a match score should trigger notification."""

    return score > 70


async def analyze_resume_vs_jobs(resume_id: int, job_ids: Iterable[int] | None = None) -> dict:
    """Analyze a resume against selected or all jobs for the user."""

    async with AsyncSessionLocal() as db:
        resume = await db.get(UserResume, resume_id)
        if not resume or resume.user_id != 1:
            return {"processed": 0, "created": 0, "updated": 0, "skipped": 0, "items": []}

        query = (
            select(Job)
            .join(JobSearchConfig, Job.search_config_id == JobSearchConfig.id)
            .where(JobSearchConfig.user_id == 1)
        )
        if job_ids:
            query = query.where(Job.id.in_(list(job_ids)))

        jobs_result = await db.execute(query)
        jobs = list(jobs_result.scalars().all())
        if not jobs:
            return {"processed": 0, "created": 0, "updated": 0, "skipped": 0, "items": []}

        user_result = await db.execute(select(User).where(User.id == 1))
        user = user_result.scalar_one_or_none()

        provider = get_llm_provider()
        created = 0
        updated = 0
        skipped = 0

        for job in jobs:
            if not any([job.title, job.company, job.salary, job.location, job.description]):
                skipped += 1
                continue

            try:
                analysis = await provider.analyze_match(
                    resume_text=resume.resume_text,
                    job_title=job.title or "",
                    job_company=job.company or "",
                    job_salary=job.salary or "",
                    job_location=job.location or "",
                    job_experience=job.experience or "",
                    job_education=job.education or "",
                    job_description=job.description or "",
                )
                _, was_created = await upsert_match_result(
                    db=db,
                    user_id=resume.user_id,
                    resume_id=resume.id,
                    job_id=job.id,
                    analysis=analysis,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

                if should_notify_match(analysis.match_score) and user and user.feishu_webhook_url:
                    try:
                        await send_feishu_notification(
                            user.feishu_webhook_url,
                            (
                                f"职位匹配提醒\n"
                                f"简历：{resume.name}\n"
                                f"职位：{job.title or '-'} / {job.company or '-'}\n"
                                f"分数：{analysis.match_score}\n"
                                f"结论：{analysis.apply_recommendation}\n"
                                f"原因：{analysis.match_reason}"
                            ),
                        )
                    except Exception:
                        # Notification failure should not fail the match analysis.
                        pass
            except Exception:
                skipped += 1
                continue

        await db.commit()

        items_result = await db.execute(
            select(MatchResult)
            .options(selectinload(MatchResult.job))
            .where(MatchResult.resume_id == resume.id)
            .order_by(MatchResult.match_score.desc(), MatchResult.updated_at.desc())
        )
        items = list(items_result.scalars().all())

        return {
            "processed": len(jobs),
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "items": items,
        }


async def upsert_match_result(
    db,
    user_id: int,
    resume_id: int,
    job_id: int,
    analysis: MatchAnalysis,
) -> tuple[MatchResult, bool]:
    """Insert or update a single match result."""

    result = await db.execute(
        select(MatchResult).where(
            MatchResult.resume_id == resume_id,
            MatchResult.job_id == job_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.match_score = analysis.match_score
        existing.match_reason = analysis.match_reason
        existing.apply_recommendation = analysis.apply_recommendation
        existing.llm_model_used = analysis.model_used
        existing.updated_at = datetime.now(UTC)
        return existing, False

    match_result = MatchResult(
        user_id=user_id,
        resume_id=resume_id,
        job_id=job_id,
        match_score=analysis.match_score,
        match_reason=analysis.match_reason,
        apply_recommendation=analysis.apply_recommendation,
        llm_model_used=analysis.model_used,
    )
    db.add(match_result)
    await db.flush()
    return match_result, True
