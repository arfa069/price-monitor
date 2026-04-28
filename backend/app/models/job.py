"""Job models for boss zhipin job crawling."""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class JobSearchConfig(Base, TimestampMixin):
    """Job search configuration for scheduled crawling."""

    __tablename__ = "job_search_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)
    keyword = Column(String(200), nullable=True)
    city_code = Column(String(20), nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    experience = Column(String(50), nullable=True)
    education = Column(String(50), nullable=True)
    url = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    notify_on_new = Column(Boolean, nullable=False, default=True)
    deactivation_threshold = Column(
        Integer, nullable=False, default=3,
        comment="Consecutive crawl misses before marking a job inactive",
    )

    # Relationships
    jobs = relationship(
        "Job", back_populates="search_config", cascade="all, delete-orphan"
    )


class Job(Base):
    """Individual job posting from boss zhipin."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_job_id", "job_id"),
        Index("ix_jobs_search_config_id", "search_config_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(500), nullable=False, unique=True)  # boss's encrypted job ID
    search_config_id = Column(
        Integer, ForeignKey("job_search_configs.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(300), nullable=True)
    company = Column(String(200), nullable=True)
    company_id = Column(String(200), nullable=True)
    salary = Column(String(100), nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    location = Column(String(200), nullable=True)
    address = Column(String(500), nullable=True)
    experience = Column(String(100), nullable=True)
    education = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    first_seen_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    last_updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    is_active = Column(Boolean, nullable=False, default=True)

    # Grace period fields for deduplication
    consecutive_miss_count = Column(Integer, nullable=False, default=0)
    # Number of consecutive crawls where this job was NOT seen.
    # Reset to 0 when the job IS seen. Deactivated when >= threshold.

    last_active_at = Column(
        DateTime(timezone=True), nullable=True,
        default=lambda: datetime.now(UTC),
    )
    # Timestamp when this job was last seen in a crawl.

    # Relationships
    search_config = relationship("JobSearchConfig", back_populates="jobs")
