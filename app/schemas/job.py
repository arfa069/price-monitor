"""Pydantic schemas for job-related API endpoints."""
from datetime import datetime

from pydantic import BaseModel, Field


class JobSearchConfigCreate(BaseModel):
    """Schema for creating a job search config."""
    name: str = Field(..., max_length=100, description="配置名称，如'北京 Python 职位'")
    keyword: str | None = Field(default=None, max_length=200, description="搜索关键词")
    city_code: str | None = Field(default=None, max_length=20, description="boss 直聘城市代码")
    salary_min: int | None = Field(default=None, ge=0, description="最低薪资（K）")
    salary_max: int | None = Field(default=None, ge=0, description="最高薪资（K）")
    experience: str | None = Field(default=None, max_length=50, description="经验要求")
    education: str | None = Field(default=None, max_length=50, description="学历要求")
    url: str = Field(..., description="boss 直聘搜索页完整 URL")
    active: bool = Field(default=True, description="是否启用定时爬取")
    notify_on_new: bool = Field(default=True, description="新职位是否发送通知")


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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
