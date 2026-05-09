"""Job search API router."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import log_audit
from app.core.permissions import require_permission
from app.core.security import get_current_user
from app.database import get_db
from app.models.job import Job, JobSearchConfig
from app.models.job_match import MatchResult, UserResume
from app.models.user import User
from app.schemas.job import (
    JobConfigCronUpdate,
    JobListResponse,
    JobResponse,
    JobSearchConfigCreate,
    JobSearchConfigResponse,
    JobSearchConfigUpdate,
)
from app.schemas.job_match import (
    MatchAnalyzeRequest,
    MatchAnalyzeResponse,
    MatchResultListResponse,
    MatchResultResponse,
    UserResumeCreate,
    UserResumeResponse,
    UserResumeUpdate,
)
from app.services.job_crawl import (
    crawl_all_job_searches_background,
    crawl_single_config_background,
)
from app.services.job_match import (
    _get_jobs_needing_analysis,
    analyze_resume_vs_jobs,
    run_match_analysis_task,
)
from app.services.scheduler_job import JobConfigScheduler
from app.services.scheduler_service import TaskStatus, get_task

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _serialize_match_result(item: MatchResult) -> MatchResultResponse:
    job = item.job
    return MatchResultResponse(
        id=item.id,
        user_id=item.user_id,
        resume_id=item.resume_id,
        job_id=item.job_id,
        match_score=item.match_score,
        match_reason=item.match_reason,
        apply_recommendation=item.apply_recommendation,
        llm_model_used=item.llm_model_used,
        created_at=item.created_at,
        updated_at=item.updated_at,
        job_title=job.title if job else None,
        job_company=job.company if job else None,
        job_salary=job.salary if job else None,
        job_location=job.location if job else None,
        job_url=job.url if job else None,
        job_description=job.description if job else None,
    )


# ── JobSearchConfig CRUD ──────────────────────────────────────────

@router.get("/configs", response_model=list[JobSearchConfigResponse])
async def list_configs(
    active: bool | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all job search configs."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    query = select(JobSearchConfig).where(JobSearchConfig.user_id == current_user.id)
    if active is not None:
        query = query.where(JobSearchConfig.active == active)
    query = query.order_by(desc(JobSearchConfig.created_at))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/configs", response_model=JobSearchConfigResponse, status_code=201)
async def create_config(
    data: JobSearchConfigCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new job search config."""
    config = JobSearchConfig(
        user_id=current_user.id,
        **data.model_dump(),
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    # Sync scheduler if cron is set
    if config.cron_expression:
        scheduler: JobConfigScheduler = getattr(request.app.state, "job_config_scheduler", None)
        if scheduler:
            scheduler.add_job(config.id, config.cron_expression, config.cron_timezone or "Asia/Shanghai")

    # Audit log
    ip_address = request.client.host if request.client else ""
    await log_audit(
        db=db,
        action="job_config.create",
        actor_user_id=current_user.id,
        target_type="job_config",
        target_id=config.id,
        details={"name": config.name},
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent", "")[:512],
        commit=True,
    )

    return config


@router.get("/resumes", response_model=list[UserResumeResponse])
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    result = await db.execute(
        select(UserResume).where(UserResume.user_id == current_user.id).order_by(desc(UserResume.created_at))
    )
    return result.scalars().all()


@router.post("/resumes", response_model=UserResumeResponse, status_code=201)
async def create_resume(
    data: UserResumeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    resume = UserResume(user_id=current_user.id, **data.model_dump())
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return resume


@router.patch("/resumes/{resume_id}", response_model=UserResumeResponse)
async def update_resume(
    resume_id: int,
    data: UserResumeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    result = await db.execute(
        select(UserResume).where(UserResume.id == resume_id, UserResume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(resume, field, value)
    await db.commit()
    await db.refresh(resume)
    return resume


@router.delete("/resumes/{resume_id}")
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    result = await db.execute(
        select(UserResume).where(UserResume.id == resume_id, UserResume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    await db.delete(resume)
    await db.commit()
    return {"message": "Resume deleted"}


@router.get("/match-results", response_model=MatchResultListResponse)
async def list_match_results(
    resume_id: int | None = None,
    job_id: int | None = None,
    min_score: int | None = Query(default=None, ge=0, le=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    query = (
        select(MatchResult)
        .join(UserResume, MatchResult.resume_id == UserResume.id)
        .join(Job, MatchResult.job_id == Job.id)
        .options(selectinload(MatchResult.job))
        .where(UserResume.user_id == current_user.id)
        .order_by(desc(MatchResult.match_score), desc(MatchResult.updated_at))
    )
    count_query = (
        select(func.count())
        .select_from(MatchResult)
        .join(UserResume, MatchResult.resume_id == UserResume.id)
        .where(UserResume.user_id == current_user.id)
    )

    if resume_id is not None:
        query = query.where(MatchResult.resume_id == resume_id)
        count_query = count_query.where(MatchResult.resume_id == resume_id)
    if job_id is not None:
        query = query.where(MatchResult.job_id == job_id)
        count_query = count_query.where(MatchResult.job_id == job_id)
    if min_score is not None:
        query = query.where(MatchResult.match_score >= min_score)
        count_query = count_query.where(MatchResult.match_score >= min_score)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    items = result.scalars().all()

    return MatchResultListResponse(
        items=[_serialize_match_result(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/match-results/analyze", response_model=MatchAnalyzeResponse)
async def trigger_match_analysis(
    data: MatchAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    resume = await db.get(UserResume, data.resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")

    result = await analyze_resume_vs_jobs(data.resume_id, data.job_ids)
    return MatchAnalyzeResponse(
        processed=result["processed"],
        created=result["created"],
        updated=result["updated"],
        skipped=result["skipped"],
        items=[_serialize_match_result(item) for item in result["items"]],
    )


@router.post("/match-results/analyze-async")
async def trigger_match_analysis_async(
    data: MatchAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger async match analysis, returning task_id for polling.

    The analysis runs in background, updating task progress.
    Poll GET /jobs/tasks/{task_id} for status.
    """

    from app.services.scheduler_service import create_task

    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    resume = await db.get(UserResume, data.resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Build job_ids list
    job_ids = data.job_ids
    if job_ids is None:
        # Get all active jobs for user
        query = select(Job.id).join(JobSearchConfig).where(JobSearchConfig.user_id == current_user.id)
        result = await db.execute(query)
        job_ids = [r for r in result.scalars().all()]

    # Check which jobs actually need analysis
    jobs_to_analyze = await _get_jobs_needing_analysis(db, data.resume_id, job_ids)
    if not jobs_to_analyze:
        return JSONResponse(content={
            "status": "completed",
            "task_id": None,
            "total": 0,
            "reason": "all_up_to_date",
            "message": "所有职位已是最新，无需分析",
        })

    # Create background task with actual count
    task = create_task(source="manual")
    task.total = len(jobs_to_analyze)

    # Start analysis in background (pass job ids that need analysis)
    asyncio.create_task(
        run_match_analysis_task(task, data.resume_id, [j.id for j in jobs_to_analyze])
    )

    return JSONResponse(content={
        "status": "pending",
        "task_id": task.task_id,
        "total": len(jobs_to_analyze),
        "message": f"分析任务已启动，通过 GET /jobs/tasks/{task.task_id} 查询进度",
    })


@router.get("/tasks/{task_id}")
async def get_match_analysis_task_status(task_id: str):
    """Get status of a match analysis task.

    Returns task progress (total/success/errors) and final results when completed.
    """
    from app.services.scheduler_service import get_task

    task = get_task(task_id)
    if not task:
        return JSONResponse(
            content={"status": "error", "reason": "task_not_found"},
            status_code=404,
        )

    response = {
        "task_id": task.task_id,
        "status": task.status.value,
        "total": task.total,
        "success": task.success,
        "errors": task.errors,
        "reason": task.reason,
    }

    # Include details when completed
    if task.status.value == "completed":
        response["details"] = task.details

    return JSONResponse(content=response)


@router.get("/configs/{config_id}", response_model=JobSearchConfigResponse)
async def get_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single config."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    result = await db.execute(
        select(JobSearchConfig).where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.patch("/configs/{config_id}", response_model=JobSearchConfigResponse)
async def update_config(
    config_id: int,
    data: JobSearchConfigUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a config."""
    result = await db.execute(
        select(JobSearchConfig).where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    update_data = data.model_dump(exclude_unset=True)

    # Only super_admin can modify cron-related fields
    cron_fields = {"cron_expression", "cron_timezone"}
    if cron_fields & set(update_data.keys()) and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：仅 super_admin 可修改定时配置",
        )

    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    # Sync scheduler if cron changed
    if "cron_expression" in update_data:
        scheduler: JobConfigScheduler = getattr(request.app.state, "job_config_scheduler", None)
        if scheduler:
            if config.cron_expression:
                scheduler.add_job(config.id, config.cron_expression, config.cron_timezone or "Asia/Shanghai")
            else:
                scheduler.remove_job(config.id)

    # Audit log
    ip_address = request.client.host if request.client else ""
    await log_audit(
        db=db,
        action="job_config.update",
        actor_user_id=current_user.id,
        target_type="job_config",
        target_id=config_id,
        details={"name": config.name, "updated_fields": list(update_data.keys())},
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent", "")[:512],
        commit=True,
    )

    return config


@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a config (cascades to jobs)."""
    result = await db.execute(
        select(JobSearchConfig).where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    config_info = {"name": config.name}

    # Remove scheduler job before deletion
    scheduler: JobConfigScheduler = getattr(request.app.state, "job_config_scheduler", None)
    if scheduler:
        scheduler.remove_job(config_id)

    await db.delete(config)
    await db.commit()

    # Audit log
    ip_address = request.client.host if request.client else ""
    await log_audit(
        db=db,
        action="job_config.delete",
        actor_user_id=current_user.id,
        target_type="job_config",
        target_id=config_id,
        details=config_info,
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent", "")[:512],
        commit=True,
    )

    return {"message": "Config deleted"}


# ── Job Listing ──────────────────────────────────────────────────

@router.get("", response_model=JobListResponse)
async def list_jobs(
    search_config_id: int | None = None,
    keyword: str | None = None,
    company: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    location: str | None = None,
    is_active: bool | None = None,
    sort_by: str = Query(default="first_seen_at"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List jobs with filtering and pagination."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    # Join with JobSearchConfig to filter by current_user
    query = select(Job).join(JobSearchConfig).where(JobSearchConfig.user_id == current_user.id)
    count_query = select(func.count()).select_from(Job).join(JobSearchConfig).where(
        JobSearchConfig.user_id == current_user.id
    )

    if search_config_id is not None:
        query = query.where(Job.search_config_id == search_config_id)
        count_query = count_query.where(Job.search_config_id == search_config_id)
    if keyword:
        keyword_filter = (
            Job.title.ilike(f"%{keyword}%") |
            Job.company.ilike(f"%{keyword}%") |
            Job.description.ilike(f"%{keyword}%")
        )
        query = query.where(keyword_filter)
        count_query = count_query.where(keyword_filter)
    if company:
        query = query.where(Job.company.ilike(f"%{company}%"))
        count_query = count_query.where(Job.company.ilike(f"%{company}%"))
    if salary_min is not None:
        query = query.where(Job.salary_min >= salary_min)
        count_query = count_query.where(Job.salary_min >= salary_min)
    if salary_max is not None:
        query = query.where(Job.salary_max <= salary_max)
        count_query = count_query.where(Job.salary_max <= salary_max)
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
        count_query = count_query.where(Job.location.ilike(f"%{location}%"))
    if is_active is not None:
        query = query.where(Job.is_active == is_active)
        count_query = count_query.where(Job.is_active == is_active)

    # Sorting
    sort_column = {
        "first_seen_at": Job.first_seen_at,
        "last_updated_at": Job.last_updated_at,
        "salary_min": Job.salary_min,
    }.get(sort_by, Job.first_seen_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    return JobListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id_str}", response_model=JobResponse)
async def get_job(
    job_id_str: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single job by boss job_id."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    result = await db.execute(
        select(Job).join(JobSearchConfig).where(
            Job.job_id == job_id_str,
            JobSearchConfig.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Crawl Triggers ───────────────────────────────────────────────

@router.post("/crawl-now")
async def crawl_now(
    current_user: User = Depends(require_permission("crawl:execute")),
):
    """Trigger crawling all active job search configs (async)."""
    task = await crawl_all_job_searches_background()
    return JSONResponse(content={
        "status": "pending",
        "task_id": task.task_id,
        "message": f"爬取任务已启动，通过 /jobs/crawl/status/{task.task_id} 查询进度",
    })


@router.post("/crawl-now/{config_id}")
async def crawl_single(
    config_id: int,
    current_user: User = Depends(require_permission("crawl:execute")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger crawling a single config (async)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")

    # 验证 config 归属
    result = await db.execute(
        select(JobSearchConfig).where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == current_user.id
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在或无权访问")

    task = await crawl_single_config_background(config_id)
    return JSONResponse(content={
        "status": "pending",
        "task_id": task.task_id,
        "message": f"爬取任务已启动，通过 /jobs/crawl/status/{task.task_id} 查询进度",
    })


@router.get("/crawl/status/{task_id}")
async def get_job_crawl_status(task_id: str):
    """Get the status of a job crawl task."""
    task = get_task(task_id)
    if not task:
        return JSONResponse(
            content={"status": "error", "reason": "task_not_found"},
            status_code=404,
        )
    return JSONResponse(content={
        "task_id": task.task_id,
        "status": task.status.value,
        "total": task.total,
        "success": task.success,
        "errors": task.errors,
    })


@router.get("/crawl/result/{task_id}")
async def get_job_crawl_result(task_id: str):
    """Get the final result of a completed job crawl task."""
    task = get_task(task_id)
    if not task:
        return JSONResponse(
            content={"status": "error", "reason": "task_not_found"},
            status_code=404,
        )
    if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
        return JSONResponse(
            content={"status": task.status.value, "task_id": task.task_id},
            status_code=202,
        )
    if task.status == TaskStatus.FAILED:
        return JSONResponse(
            content={"status": "error", "task_id": task.task_id, "reason": task.reason},
            status_code=500,
        )
    return JSONResponse(content={
        "status": "completed",
        "task_id": task.task_id,
        "total": task.total,
        "success": task.success,
        "errors": task.errors,
    })


# ── Per-Config Cron Management ──────────────────────────────

@router.patch("/configs/{config_id}/cron", response_model=JobSearchConfigResponse)
async def update_config_cron(
    config_id: int,
    data: JobConfigCronUpdate,
    request: Request,
    current_user: User = Depends(require_permission("schedule:configure")),
    db: AsyncSession = Depends(get_db),
):
    """Update only the cron settings for a job search config.

    Null cron_expression disables scheduled crawling for this config.
    """
    result = await db.execute(
        select(JobSearchConfig).where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    config.cron_expression = data.cron_expression
    config.cron_timezone = data.cron_timezone or "Asia/Shanghai"

    await db.commit()
    await db.refresh(config)

    # Sync scheduler
    scheduler: JobConfigScheduler = getattr(request.app.state, "job_config_scheduler", None)
    if scheduler:
        if config.cron_expression:
            scheduler.add_job(config.id, config.cron_expression, config.cron_timezone)
        else:
            scheduler.remove_job(config.id)

    # Audit log
    ip_address = request.client.host if request.client else ""
    await log_audit(
        db=db,
        action="schedule.update",
        actor_user_id=current_user.id,
        target_type="job_config",
        target_id=config.id,
        details={"config_name": config.name, "cron_expression": data.cron_expression},
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent", "")[:512],
        commit=True,
    )

    return config


@router.get("/scheduler/job-configs")
async def get_job_config_schedules(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get next run times for all per-config job crawl schedules."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")

    # 获取当前用户的 config_ids
    result = await db.execute(
        select(JobSearchConfig.id).where(JobSearchConfig.user_id == current_user.id)
    )
    user_config_ids = set(result.scalars().all())

    scheduler: JobConfigScheduler = getattr(request.app.state, "job_config_scheduler", None)
    if not scheduler:
        return {"configs": []}
    schedules = scheduler.get_next_run_times()

    # 只返回当前用户拥有的配置
    return {"configs": [
        {"config_id": cid, **info} for cid, info in schedules.items() if cid in user_config_ids
    ]}
