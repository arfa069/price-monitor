"""Resume-job match analysis service."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.job import Job, JobSearchConfig
from app.models.job_match import MatchResult, UserResume
from app.services.llm_provider import MatchAnalysis, get_llm_provider
from app.services.notification import send_feishu_notification
from app.services.user_config_cache import get_cached_user_config


async def _get_jobs_needing_analysis(
    db,
    resume_id: int,
    job_ids: list[int],
) -> list:
    """Return jobs that need match analysis for the given resume.

    A job needs analysis if:
    1. No existing MatchResult for (resume_id, job_id)
    2. Job was updated after the last MatchResult analysis
    """

    # 1. Get existing match results for this resume
    existing_result = await db.execute(
        select(MatchResult).where(MatchResult.resume_id == resume_id)
    )
    match_map = {m.job_id: m for m in existing_result.scalars().all()}

    # 2. Get target jobs
    jobs_result = await db.execute(select(Job).where(Job.id.in_(job_ids)))
    jobs = list(jobs_result.scalars().all())

    need_analysis = []
    for job in jobs:
        match = match_map.get(job.id)
        if not match:
            need_analysis.append(job)
        elif job.last_updated_at > match.updated_at:
            need_analysis.append(job)
        # else: already analyzed and job hasn't changed, skip

    return need_analysis


async def run_match_analysis_task(
    task,
    resume_id: int,
    job_ids: list[int],
    db=None,
) -> None:
    """Run match analysis in background, updating task progress.

    Args:
        task: The CrawlTask to update with progress
        resume_id: The resume to analyze against
        job_ids: Candidate job IDs to consider
        db: Optional database session (for testing injection)
    """
    from app.services.scheduler_service import TaskStatus

    task.status = TaskStatus.RUNNING

    try:
        if db is not None:
            await _execute_match_analysis(task, resume_id, job_ids, db)
        else:
            async with AsyncSessionLocal() as db:
                await _execute_match_analysis(task, resume_id, job_ids, db)
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.reason = str(e)


async def _execute_match_analysis(task, resume_id, job_ids, db) -> None:
    """Internal: execute match analysis with an open db session."""
    from app.services.scheduler_service import TaskStatus

    # 1. Get the resume
    resume = await db.get(UserResume, resume_id)
    if not resume or resume.user_id != 1:
        task.status = TaskStatus.FAILED
        task.reason = "resume_not_found"
        return

    # 2. Filter to jobs needing analysis
    jobs_to_analyze = await _get_jobs_needing_analysis(db, resume_id, job_ids)
    task.total = len(jobs_to_analyze)

    if not jobs_to_analyze:
        task.status = TaskStatus.COMPLETED
        task.reason = "all_up_to_date"
        return

    # 3. Get user for notifications (cached)
    user = await get_cached_user_config(db)

    # 4. Analyze in batches of 3 (concurrent)
    BATCH_SIZE = 10
    provider = get_llm_provider()
    notify_jobs = []  # 高分职位，汇总后发一条飞书

    for i in range(0, len(jobs_to_analyze), BATCH_SIZE):
        batch = jobs_to_analyze[i : i + BATCH_SIZE]

        # 过滤无内容的 job
        valid_jobs = [
            j
            for j in batch
            if any([j.title, j.company, j.salary, j.location, j.description])
        ]

        if not valid_jobs:
            task.errors += len(batch)
            continue

        # 并发分析
        tasks = [
            provider.analyze_match(
                resume_text=resume.resume_text,
                job_title=job.title or "",
                job_company=job.company or "",
                job_salary=job.salary or "",
                job_location=job.location or "",
                job_experience=job.experience or "",
                job_education=job.education or "",
                job_description=job.description or "",
            )
            for job in valid_jobs
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 逐个 upsert + commit
        for job, result in zip(valid_jobs, results):
            if isinstance(result, Exception):
                task.errors += 1
                continue

            await upsert_match_result(
                db=db,
                user_id=resume.user_id,
                resume_id=resume.id,
                job_id=job.id,
                analysis=result,
            )
            task.success += 1
            await db.commit()

            if should_notify_match(result.match_score):
                notify_jobs.append((job, result))

    # 汇总飞书通知（只发一条）
    webhook_url = user.get("feishu_webhook_url") if user else None
    if notify_jobs and webhook_url:
        try:
            lines = [
                f"职位匹配提醒（共 {len(notify_jobs)} 个高分职位）",
                f"简历：{resume.name}",
            ]
            for job, analysis in sorted(
                notify_jobs, key=lambda x: x[1].match_score, reverse=True
            ):
                lines.append(
                    f"• {job.title or '-'} / {job.company or '-'}（{analysis.match_score}分）"
                )
            lines.append(f"结论：{analysis.apply_recommendation}")
            await send_feishu_notification(webhook_url, "\n".join(lines))
        except Exception:
            pass

    task.status = TaskStatus.COMPLETED


def should_notify_match(score: int) -> bool:
    """Whether a match score should trigger notification."""

    return score > 70


async def analyze_resume_vs_jobs(
    resume_id: int, job_ids: Iterable[int] | None = None
) -> dict:
    """Analyze a resume against selected or all jobs for the user."""

    async with AsyncSessionLocal() as db:
        resume = await db.get(UserResume, resume_id)
        if not resume or resume.user_id != 1:
            return {
                "processed": 0,
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "items": [],
            }

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
            return {
                "processed": 0,
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "items": [],
            }

        user = await get_cached_user_config(db)
        webhook_url = user.get("feishu_webhook_url") if user else None

        provider = get_llm_provider()
        created = 0
        updated = 0
        skipped = 0
        BATCH_SIZE = 10
        notify_jobs = []

        # Batch valid jobs first
        valid_jobs = [
            j
            for j in jobs
            if any([j.title, j.company, j.salary, j.location, j.description])
        ]
        skipped = len(jobs) - len(valid_jobs)

        for i in range(0, len(valid_jobs), BATCH_SIZE):
            batch = valid_jobs[i : i + BATCH_SIZE]

            # Concurrent LLM analysis for the batch
            tasks = [
                provider.analyze_match(
                    resume_text=resume.resume_text,
                    job_title=job.title or "",
                    job_company=job.company or "",
                    job_salary=job.salary or "",
                    job_location=job.location or "",
                    job_experience=job.experience or "",
                    job_education=job.education or "",
                    job_description=job.description or "",
                )
                for job in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for job, result in zip(batch, results):
                if isinstance(result, Exception):
                    skipped += 1
                    continue

                _, was_created = await upsert_match_result(
                    db=db,
                    user_id=resume.user_id,
                    resume_id=resume.id,
                    job_id=job.id,
                    analysis=result,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                await db.commit()

                if should_notify_match(result.match_score):
                    notify_jobs.append((job, result))

        # Batch notification (one message with all high-score jobs)
        if notify_jobs and webhook_url:
            try:
                lines = [
                    f"职位匹配提醒（共 {len(notify_jobs)} 个高分职位）",
                    f"简历：{resume.name}",
                ]
                for job, analysis in sorted(
                    notify_jobs, key=lambda x: x[1].match_score, reverse=True
                ):
                    lines.append(
                        f"• {job.title or '-'} / {job.company or '-'}（{analysis.match_score}分）"
                    )
                await send_feishu_notification(webhook_url, "\n".join(lines))
            except Exception:
                pass

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
    """Insert or update a single match result using direct SQL."""
    from sqlalchemy import text

    # 直接用 SQL 查询是否存在
    result = await db.execute(
        text(
            "SELECT id FROM match_results WHERE resume_id = :resume_id AND job_id = :job_id"
        ),
        {"resume_id": resume_id, "job_id": job_id},
    )
    existing_id = result.scalar_one_or_none()

    if existing_id:
        # 更新
        await db.execute(
            text("""
                UPDATE match_results
                SET match_score = :score, match_reason = :reason,
                    apply_recommendation = :rec, llm_model_used = :model,
                    updated_at = NOW()
                WHERE id = :id
            """),
            {
                "score": analysis.match_score,
                "reason": analysis.match_reason,
                "rec": analysis.apply_recommendation,
                "model": analysis.model_used,
                "id": existing_id,
            },
        )
        return await db.get(MatchResult, existing_id), False

    # 插入
    result = await db.execute(
        text("""
            INSERT INTO match_results
            (user_id, resume_id, job_id, match_score, match_reason, apply_recommendation, llm_model_used, created_at, updated_at)
            VALUES (:user_id, :resume_id, :job_id, :score, :reason, :rec, :model, NOW(), NOW())
            RETURNING id
        """),
        {
            "user_id": user_id,
            "resume_id": resume_id,
            "job_id": job_id,
            "score": analysis.match_score,
            "reason": analysis.match_reason,
            "rec": analysis.apply_recommendation,
            "model": analysis.model_used,
        },
    )
    new_id = result.scalar()
    return await db.get(MatchResult, new_id), True
