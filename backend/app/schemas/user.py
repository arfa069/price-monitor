"""User configuration schemas."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_CRON_SEGMENT_RE = __import__("re").compile(
    r"^(\*|[0-9]+(-[0-9]+)?)(/[0-9]+)?(,(\*|[0-9]+(-[0-9]+)?)(/[0-9]+)?)*$"
)


class UserConfigCreate(BaseModel):
    """Schema for creating user configuration."""
    feishu_webhook_url: str = Field(default="", description="Feishu webhook URL for notifications")
    crawl_frequency_hours: int = Field(default=1, ge=1, le=168, description="Crawl frequency in hours")
    data_retention_days: int = Field(default=365, ge=1, le=3650, description="Data retention period in days")
    crawl_cron: str | None = Field(default=None, description="Cron expression (5-segment)")
    crawl_timezone: str | None = Field(default="Asia/Shanghai", description="Timezone for cron")

    @field_validator("crawl_cron")
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
        if v is None:
            return v
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError("Cron 必须是 5 段格式（分 时 日 月 周）")
        for i, seg in enumerate(parts):
            if not _CRON_SEGMENT_RE.match(seg):
                raise ValueError(f"Cron 第{i+1}段 '{seg}' 格式不正确")
        return v

    @field_validator("crawl_timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            import zoneinfo
            zoneinfo.ZoneInfo(v)
        except Exception:
            raise ValueError(f"时区 '{v}' 不被支持")
        return v


class UserConfigUpdate(BaseModel):
    """Schema for updating user configuration."""
    feishu_webhook_url: str | None = Field(default=None, description="Feishu webhook URL")
    crawl_frequency_hours: int | None = Field(default=None, ge=1, le=168)
    data_retention_days: int | None = Field(default=None, ge=1, le=3650)
    crawl_cron: str | None = Field(default=None, description="Cron expression (5-segment)")
    crawl_timezone: str | None = Field(default=None, description="Timezone for cron")
    job_crawl_cron: str | None = Field(default=None, description="Job crawl cron expression")

    @field_validator("crawl_cron")
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v.strip() == "":
            return None
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError("Cron 必须是 5 段格式（分 时 日 月 周）")
        for i, seg in enumerate(parts):
            if not _CRON_SEGMENT_RE.match(seg):
                raise ValueError(f"Cron 第{i+1}段 '{seg}' 格式不正确")
        return v

    @field_validator("crawl_timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            import zoneinfo
            zoneinfo.ZoneInfo(v)
        except Exception:
            raise ValueError(f"时区 '{v}' 不被支持")
        return v

    @field_validator("job_crawl_cron")
    @classmethod
    def validate_job_cron(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v.strip() == "":
            return None
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError("Job cron 必须是 5 段格式（分 时 日 月 周）")
        for i, seg in enumerate(parts):
            if not _CRON_SEGMENT_RE.match(seg):
                raise ValueError(f"Cron 第{i+1}段 '{seg}' 格式不正确")
        return v


class UserConfigResponse(BaseModel):
    """Schema for user configuration response."""
    id: int
    username: str
    feishu_webhook_url: str | None = ""
    crawl_frequency_hours: int = 1
    data_retention_days: int = 365
    crawl_cron: str | None = None
    crawl_timezone: str | None = "Asia/Shanghai"
    job_crawl_cron: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserConfigDefaults(BaseModel):
    """Default configuration values."""
    crawl_frequency_hours: int = 1
    data_retention_days: int = 365
    crawl_cron: str | None = None
    crawl_timezone: str | None = "Asia/Shanghai"
    job_crawl_cron: str | None = "0 9 * * *"


class JobCrawlCronUpdate(BaseModel):
    """Schema for updating job crawl cron expression."""
    job_crawl_cron: str | None = None
