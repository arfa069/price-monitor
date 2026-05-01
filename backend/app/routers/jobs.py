"""Job search API router."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import Job, JobSearchConfig
from app.schemas.job import (
    JobCrawlResult,
    JobListResponse,
    JobResponse,
    JobSearchConfigCreate,
    JobSearchConfigResponse,
    JobSearchConfigUpdate,
)
from app.services.job_crawl import (
    crawl_all_job_searches,
    crawl_single_config,
    crawl_single_config_background,
    crawl_all_job_searches_background,
)
from app.services.scheduler_service import TaskStatus, get_task

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ── JobSearchConfig CRUD ──────────────────────────────────────────

@router.get("/configs", response_model=list[JobSearchConfigResponse])
async def list_configs(
    active: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all job search configs."""
    query = select(JobSearchConfig).where(JobSearchConfig.user_id == 1)
    if active is not None:
        query = query.where(JobSearchConfig.active == active)
    query = query.order_by(desc(JobSearchConfig.created_at))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/configs", response_model=JobSearchConfigResponse, status_code=201)
async def create_config(
    data: JobSearchConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new job search config."""
    config = JobSearchConfig(
        user_id=1,
        **data.model_dump(),
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/configs/{config_id}", response_model=JobSearchConfigResponse)
async def get_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single config."""
    result = await db.execute(
        select(JobSearchConfig).where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == 1,
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
    db: AsyncSession = Depends(get_db),
):
    """Update a config."""
    result = await db.execute(
        select(JobSearchConfig).where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == 1,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/configs/{config_id}")
async def delete_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a config (cascades to jobs)."""
    result = await db.execute(
        select(JobSearchConfig).where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == 1,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    await db.delete(config)
    await db.commit()
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
    db: AsyncSession = Depends(get_db),
):
    """List jobs with filtering and pagination."""
    # Join with JobSearchConfig to filter by user_id=1
    query = select(Job).join(JobSearchConfig).where(JobSearchConfig.user_id == 1)
    count_query = select(func.count()).select_from(Job).join(JobSearchConfig).where(
        JobSearchConfig.user_id == 1
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
async def get_job(job_id_str: str, db: AsyncSession = Depends(get_db)):
    """Get a single job by boss job_id."""
    result = await db.execute(
        select(Job).join(JobSearchConfig).where(
            Job.job_id == job_id_str,
            JobSearchConfig.user_id == 1,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Crawl Triggers ───────────────────────────────────────────────

@router.post("/crawl-now")
async def crawl_now():
    """Trigger crawling all active job search configs (async)."""
    task = await crawl_all_job_searches_background()
    return JSONResponse(content={
        "status": "pending",
        "task_id": task.task_id,
        "message": f"爬取任务已启动，通过 /jobs/crawl/status/{task.task_id} 查询进度",
    })


@router.post("/crawl-now/{config_id}")
async def crawl_single(config_id: int):
    """Trigger crawling a single config (async)."""
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
