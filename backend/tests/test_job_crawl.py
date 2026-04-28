"""Tests for job crawling service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestParseSalary:
    """Test salary string parsing."""

    def test_parse_salary_range_k(self):
        from app.services.job_crawl import parse_salary
        assert parse_salary("20-40K") == (20, 40)
        assert parse_salary("15-30k") == (15, 30)

    def test_parse_salary_with_bonus(self):
        from app.services.job_crawl import parse_salary
        assert parse_salary("20-40K·14薪") == (20, 40)
        assert parse_salary("30-50K·16薪") == (30, 50)

    def test_parse_salary_single_value(self):
        from app.services.job_crawl import parse_salary
        assert parse_salary("25K") == (25, 25)
        assert parse_salary("15k") == (15, 15)

    def test_parse_salary_negotiable(self):
        from app.services.job_crawl import parse_salary
        assert parse_salary("面议") == (None, None)
        assert parse_salary("薪资面议") == (None, None)

    def test_parse_salary_none(self):
        from app.services.job_crawl import parse_salary
        assert parse_salary(None) == (None, None)

    def test_parse_salary_empty(self):
        from app.services.job_crawl import parse_salary
        assert parse_salary("") == (None, None)

    def test_parse_salary_invalid(self):
        from app.services.job_crawl import parse_salary
        assert parse_salary("面薪") == (None, None)
        assert parse_salary("未知格式") == (None, None)

    def test_parse_salary_edge_cases(self):
        from app.services.job_crawl import parse_salary
        # Leading/trailing whitespace
        assert parse_salary("  20-40K  ") == (20, 40)
        # Mixed case K
        assert parse_salary("20-40k") == (20, 40)
        # Salary with spaces (spaces are stripped, so still parses)
        assert parse_salary("20 - 40K") == (20, 40)
        # Very large numbers
        assert parse_salary("100-200K") == (100, 200)


class TestProcessJobResults:
    """Test process_job_results dedup and grace period logic."""

    @pytest.mark.asyncio
    async def test_process_job_results_creates_new_jobs(self):
        """New jobs should be inserted with is_active=True."""
        from app.services.job_crawl import process_job_results

        mock_config = MagicMock()
        mock_config.id = 1
        mock_config.notify_on_new = False
        mock_config.deactivation_threshold = 3

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar_one_or_none.return_value = None

        mock_db = MagicMock()
        mock_db.get = AsyncMock(return_value=mock_config)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        with patch("app.services.job_crawl.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            result = await process_job_results(1, [{"job_id": "abc123", "title": "Dev"}], 1)

        assert result["new_count"] == 1
        assert result["deactivated_count"] == 0

    @pytest.mark.asyncio
    async def test_process_job_results_updates_existing_job(self):
        """Existing jobs should be updated and reactivated."""
        from app.services.job_crawl import process_job_results

        mock_config = MagicMock()
        mock_config.id = 1
        mock_config.notify_on_new = False
        mock_config.deactivation_threshold = 3

        existing_job = MagicMock()
        existing_job.job_id = "abc123"
        existing_job.search_config_id = 1
        existing_job.is_active = True
        existing_job.consecutive_miss_count = 1
        existing_job.title = "Old Title"
        existing_job.last_active_at = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_job]
        mock_result.scalar_one_or_none.return_value = existing_job

        mock_db = MagicMock()
        mock_db.get = AsyncMock(return_value=mock_config)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        with patch("app.services.job_crawl.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            result = await process_job_results(1, [{"job_id": "abc123", "title": "New Title"}], 1)

        assert result["new_count"] == 0
        assert result["updated_count"] == 1
        assert existing_job.is_active is True
        assert existing_job.consecutive_miss_count == 0  # Reset on presence

    @pytest.mark.asyncio
    async def test_process_job_results_grace_period_deactivation(self):
        """Job should be deactivated when threshold reached (threshold=2, miss_count goes 1->2)."""
        from app.services.job_crawl import process_job_results

        mock_config = MagicMock()
        mock_config.id = 999
        mock_config.notify_on_new = False
        mock_config.deactivation_threshold = 2

        # Job "abc" is NOT in current crawl (seen_job_ids only contains "xyz")
        existing_job = MagicMock()
        existing_job.job_id = "abc"
        existing_job.search_config_id = 999
        existing_job.is_active = True
        existing_job.consecutive_miss_count = 1
        existing_job.last_active_at = None

        # Current crawl has job "xyz" but NOT "abc" → abc gets deactivation logic
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_job]
        mock_result.scalar_one_or_none.return_value = None

        mock_db = MagicMock()
        mock_db.get = AsyncMock(return_value=mock_config)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        with patch("app.services.job_crawl.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            # Crawl has "xyz" (so seen_job_ids is non-empty), but "abc" is absent
            result = await process_job_results(999, [{"job_id": "xyz", "title": "Other"}], 1)

        assert result["deactivated_count"] == 1
        assert existing_job.is_active is False
        assert existing_job.consecutive_miss_count == 2

    @pytest.mark.asyncio
    async def test_process_job_results_grace_period_not_yet_deactivated(self):
        """Job should NOT be deactivated until threshold is reached (threshold=2, miss_count 0->1)."""
        from app.services.job_crawl import process_job_results

        mock_config = MagicMock()
        mock_config.id = 999
        mock_config.notify_on_new = False
        mock_config.deactivation_threshold = 2

        # Job "abc" is NOT in current crawl (seen_job_ids only contains "xyz")
        existing_job = MagicMock()
        existing_job.job_id = "abc"
        existing_job.search_config_id = 999
        existing_job.is_active = True
        existing_job.consecutive_miss_count = 0
        existing_job.last_active_at = None

        # Current crawl has job "xyz" but NOT "abc" → abc gets miss counter logic
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_job]
        mock_result.scalar_one_or_none.return_value = None

        mock_db = MagicMock()
        mock_db.get = AsyncMock(return_value=mock_config)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        with patch("app.services.job_crawl.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            # Crawl has "xyz" (so seen_job_ids is non-empty), but "abc" is absent
            result = await process_job_results(999, [{"job_id": "xyz", "title": "Other"}], 1)

        assert result["deactivated_count"] == 0
        assert existing_job.is_active is True
        assert existing_job.consecutive_miss_count == 1  # Incremented but not deactivated
