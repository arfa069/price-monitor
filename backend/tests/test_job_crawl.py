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
        mock_db.flush = AsyncMock()

        with patch("app.services.job_crawl.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            with patch("app.services.job_crawl.update_job_detail", new_callable=AsyncMock):
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
        mock_db.flush = AsyncMock()

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
        mock_db.flush = AsyncMock()

        with patch("app.services.job_crawl.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            # Crawl has "xyz" (so seen_job_ids is non-empty), but "abc" is absent
            result = await process_job_results(999, [{"job_id": "xyz", "title": "Other"}], 1)

        assert result["deactivated_count"] == 0
        assert existing_job.is_active is True
        assert existing_job.consecutive_miss_count == 1  # Incremented but not deactivated


class TestCrawlDetail:
    """Test job detail scraping."""

    @pytest.mark.asyncio
    async def test_crawl_detail_success(self):
        """crawl_detail should return parsed job details."""
        from app.platforms.boss import BossZhipinAdapter

        with patch.object(BossZhipinAdapter, "_acquire_cookies", new_callable=AsyncMock, return_value=True):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "code": 0,
                "zpData": {
                    "jobInfo": {
                        "jobName": "Java",
                        "salaryDesc": "10-15K·14薪",
                        "locationName": "深圳",
                        "address": "深圳南山区前海周大福金融大厦1401-05",
                        "experienceName": "在校/应届",
                        "degreeName": "本科",
                        "postDescription": "岗位职责: ...",
                    },
                    "bossInfo": {"name": "李俊滨", "title": "AI全栈工程师"},
                    "brandComInfo": {"brandName": "望尘科技"},
                },
            }

            with patch("app.platforms.boss.CffiSession") as mock_session_cls:
                mock_session = MagicMock()
                mock_session.get.return_value = mock_response
                mock_session.cookies.get_dict.return_value = {}
                mock_session_cls.return_value = mock_session

                adapter = BossZhipinAdapter()
                result = await adapter.crawl_detail("test_security_id")

        assert result["success"] is True
        assert result["detail"]["title"] == "Java"
        assert result["detail"]["address"] == "深圳南山区前海周大福金融大厦1401-05"
        assert result["detail"]["description"] == "岗位职责: ..."
        assert result["detail"]["company"] == "望尘科技"

    @pytest.mark.asyncio
    async def test_crawl_detail_no_cookies(self):
        """crawl_detail should fail gracefully without cookies."""
        from app.platforms.boss import BossZhipinAdapter

        with patch.object(BossZhipinAdapter, "_acquire_cookies", new_callable=AsyncMock, return_value=False):
            adapter = BossZhipinAdapter()
            result = await adapter.crawl_detail("test_security_id")

        assert result["success"] is False
        assert "cookies" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_crawl_detail_api_error(self):
        """crawl_detail should handle API errors gracefully."""
        from app.platforms.boss import BossZhipinAdapter

        with patch.object(BossZhipinAdapter, "_acquire_cookies", new_callable=AsyncMock, return_value=True):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"code": 37, "message": "Cookie expired"}

            with patch("app.platforms.boss.CffiSession") as mock_session_cls:
                mock_session = MagicMock()
                mock_session.get.return_value = mock_response
                mock_session.cookies.get_dict.return_value = {}
                mock_session_cls.return_value = mock_session

                adapter = BossZhipinAdapter()
                result = await adapter.crawl_detail("test_security_id")

        assert result["success"] is False
        assert "code=37" in result["error"]


class TestUpdateJobDetail:
    """Test update_job_detail service function."""

    @pytest.mark.asyncio
    async def test_update_job_detail_success(self):
        """update_job_detail should update job record with detail data."""
        from app.services.job_crawl import update_job_detail

        mock_job = MagicMock()
        mock_job.id = 1
        mock_job.job_id = "test_encrypt_id"
        mock_job.description = None
        mock_job.address = None

        mock_db = MagicMock()
        mock_db.get = AsyncMock(return_value=mock_job)
        mock_db.commit = AsyncMock()

        mock_adapter = MagicMock()
        mock_adapter.crawl_detail = AsyncMock(return_value={
            "success": True,
            "detail": {
                "description": "岗位职责: ...",
                "address": "深圳南山区",
                "title": "Java",
            },
        })

        with patch("app.services.job_crawl.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            with patch("app.platforms.BossZhipinAdapter") as mock_adapter_cls:
                mock_adapter_cls.return_value = mock_adapter
                result = await update_job_detail(1)

        assert result["success"] is True
        assert result["detail"]["description"] == "岗位职责: ..."
        assert mock_job.description == "岗位职责: ..."
        assert mock_job.address == "深圳南山区"

    @pytest.mark.asyncio
    async def test_update_job_detail_not_found(self):
        """update_job_detail should return error if job not found."""
        from app.services.job_crawl import update_job_detail

        mock_db = MagicMock()
        mock_db.get = AsyncMock(return_value=None)

        with patch("app.services.job_crawl.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db
            mock_session.return_value.__aexit__.return_value = None

            result = await update_job_detail(999)

        assert result["success"] is False
        assert "not found" in result["error"].lower()
