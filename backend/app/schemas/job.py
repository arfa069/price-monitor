"""Pydantic schemas for job-related API endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class JobSearchConfigCreate(BaseModel):
    """Schema for creating a job search config."""

    name: str = Field(..., max_length=100)
    keyword: str | None = Field(default=None, max_length=200)
    city_code: str | None = Field(default=None, max_length=20)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    experience: str | None = Field(default=None, max_length=50)
    education: str | None = Field(default=None, max_length=50)
    url: str
    active: bool = True
    notify_on_new: bool = True
    deactivation_threshold: int = Field(default=3, ge=1)
    cron_expression: str | None = Field(default=None, max_length=100)
    cron_timezone: str | None = Field(default=None, max_length=50)
    enable_match_analysis: bool = False


class JobSearchConfigUpdate(BaseModel):
    """Schema for updating a job search config."""

    name: str | None = Field(default=None, max_length=100)
    keyword: str | None = Field(default=None, max_length=200)
    city_code: str | None = Field(default=None, max_length=20)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    experience: str | None = Field(default=None, max_length=50)
    education: str | None = Field(default=None, max_length=50)
    url: str | None = None
    active: bool | None = None
    notify_on_new: bool | None = None
    deactivation_threshold: int | None = Field(default=None, ge=1)
    cron_expression: str | None = Field(default=None, max_length=100)
    cron_timezone: str | None = Field(default=None, max_length=50)
    enable_match_analysis: bool | None = None


class JobSearchConfigResponse(BaseModel):
    """Schema for job search config response."""

    id: int
    user_id: int
    name: str
    keyword: str | None
    city_code: str | None
    salary_min: int | None
    salary_max: int | None
    experience: str | None
    education: str | None
    url: str
    active: bool
    notify_on_new: bool
    deactivation_threshold: int
    cron_expression: str | None
    cron_timezone: str | None
    enable_match_analysis: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobConfigCronUpdate(BaseModel):
    """Schema for updating only the cron settings of a job search config."""

    cron_expression: str | None = Field(default=None, max_length=100)
    cron_timezone: str | None = Field(default=None, max_length=50)


class JobResponse(BaseModel):
    """Schema for job response."""

    id: int
    job_id: str
    search_config_id: int
    title: str | None
    company: str | None
    company_id: str | None
    salary: str | None
    salary_min: int | None
    salary_max: int | None
    location: str | None
    experience: str | None
    education: str | None
    description: str | None
    url: str | None
    first_seen_at: datetime
    last_updated_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class JobCrawlResult(BaseModel):
    """Schema for job crawl result."""

    new_count: int
    updated_count: int
    deactivated_count: int = 0


class JobListResponse(BaseModel):
    """Paginated job list response."""

    items: list[JobResponse]
    total: int
    page: int
    page_size: int
