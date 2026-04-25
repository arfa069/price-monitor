"""Job search API router."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import Job, JobSearchConfig
from app.schemas.job import (
    JobCrawlResult,
    JobResponse,
    JobSearchConfigCreate,
    JobSearchConfigResponse,
    JobSearchConfigUpdate,
)
from app.services.job_crawl import crawl_all_job_searches, crawl_single_config

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

@router.get("", response_model=list[JobResponse])
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

    if search_config_id is not None:
        query = query.where(Job.search_config_id == search_config_id)
    if keyword:
        query = query.where(
            Job.title.ilike(f"%{keyword}%") |
            Job.company.ilike(f"%{keyword}%") |
            Job.description.ilike(f"%{keyword}%")
        )
    if company:
        query = query.where(Job.company.ilike(f"%{company}%"))
    if salary_min is not None:
        query = query.where(Job.salary_min >= salary_min)
    if salary_max is not None:
        query = query.where(Job.salary_max <= salary_max)
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
    if is_active is not None:
        query = query.where(Job.is_active == is_active)

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

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    return result.scalars().all()


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
    """Trigger crawling all active job search configs."""
    result = await crawl_all_job_searches(source="manual")
    return JSONResponse(content={
        "status": result["status"],
        "total": result["total"],
        "success": result["success"],
        "errors": result["errors"],
    })


@router.post("/crawl-now/{config_id}", response_model=JobCrawlResult)
async def crawl_single(config_id: int):
    """Trigger crawling a single config."""
    result = await crawl_single_config(config_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    return JobCrawlResult(**result)
