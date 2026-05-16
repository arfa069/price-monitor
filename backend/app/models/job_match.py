"""Job match models."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class UserResume(Base, TimestampMixin):
    """User uploaded resume."""

    __tablename__ = "jobs_resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    resume_text = Column(Text, nullable=False)

    match_results = relationship("MatchResult", back_populates="resume", cascade="all, delete-orphan")


class MatchResult(Base):
    """Stored resume-job match result."""

    __tablename__ = "jobs_match_results"
    __table_args__ = (UniqueConstraint("resume_id", "job_id", name="uq_resume_job"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(Integer, ForeignKey("jobs_resumes.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    match_score = Column(Integer, nullable=False)
    match_reason = Column(Text, nullable=True)
    apply_recommendation = Column(String(50), nullable=True)
    llm_model_used = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    resume = relationship("UserResume", back_populates="match_results")
    job = relationship("Job", back_populates="match_results")
