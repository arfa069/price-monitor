"""Tests for job crawling service."""
import pytest


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
