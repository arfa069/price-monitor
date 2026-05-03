"""Unit tests for job match service helpers."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


def test_should_notify_match_threshold():
    """Scores above 70 should notify."""
    from app.services.job_match import should_notify_match

    assert should_notify_match(71) is True
    assert should_notify_match(100) is True
    assert should_notify_match(70) is False


@pytest.mark.asyncio
async def test_upsert_match_result_creates_new_record():
    """upsert_match_result inserts a new MatchResult when none exists."""
    from app.services.job_match import upsert_match_result
    from app.services.llm_provider import MatchAnalysis

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    analysis = MatchAnalysis(
        match_score=83,
        match_reason="Good backend fit",
        apply_recommendation="可以考虑",
        model_used="gpt-4o-mini",
    )

    result, was_created = await upsert_match_result(
        db=mock_db,
        user_id=1,
        resume_id=2,
        job_id=3,
        analysis=analysis,
    )

    assert was_created is True
    assert result.match_score == 83
    assert result.resume_id == 2
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_match_result_updates_existing_record():
    """upsert_match_result updates an existing MatchResult in-place."""
    from app.services.job_match import upsert_match_result
    from app.services.llm_provider import MatchAnalysis

    existing = MagicMock()
    existing.match_score = 50
    existing.match_reason = "Old"
    existing.apply_recommendation = "不太匹配"
    existing.llm_model_used = "old-model"
    existing.updated_at = datetime.now(UTC)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    analysis = MatchAnalysis(
        match_score=92,
        match_reason="Excellent fit",
        apply_recommendation="强烈推荐",
        model_used="gpt-4o-mini",
    )

    result, was_created = await upsert_match_result(
        db=mock_db,
        user_id=1,
        resume_id=2,
        job_id=3,
        analysis=analysis,
    )

    assert was_created is False
    assert result is existing
    assert existing.match_score == 92
    assert existing.apply_recommendation == "强烈推荐"
