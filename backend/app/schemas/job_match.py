"""Schemas for resume and job match endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class UserResumeCreate(BaseModel):
    name: str = Field(..., max_length=100)
    resume_text: str = Field(..., min_length=1)


class UserResumeUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    resume_text: str | None = None


class UserResumeResponse(BaseModel):
    id: int
    user_id: int
    name: str
    resume_text: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MatchAnalyzeRequest(BaseModel):
    resume_id: int
    job_ids: list[int] | None = None


class MatchResultResponse(BaseModel):
    id: int
    user_id: int
    resume_id: int
    job_id: int
    match_score: int
    match_reason: str | None
    apply_recommendation: str | None
    llm_model_used: str | None
    created_at: datetime
    updated_at: datetime
    job_title: str | None = None
    job_company: str | None = None
    job_salary: str | None = None
    job_location: str | None = None
    job_url: str | None = None
    job_description: str | None = None

    model_config = {"from_attributes": True}


class MatchResultListResponse(BaseModel):
    items: list[MatchResultResponse]
    total: int
    page: int
    page_size: int


class MatchAnalyzeResponse(BaseModel):
    processed: int
    created: int
    updated: int
    skipped: int
    items: list[MatchResultResponse]
