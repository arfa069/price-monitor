"""Real Feishu webhook integration tests (requires real webhook URL).

This module performs live API calls to Feishu webhook.
Run manually with: pytest tests/test_feishu_real.py -v -s
Or set FEISHU_WEBHOOK_URL environment variable.
"""
from __future__ import annotations

import os

import pytest


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("FEISHU_WEBHOOK_URL") in (None, "", "skip"),
    reason="FEISHU_WEBHOOK_URL not configured",
)
async def test_feishu_webhook_real_call():
    """Send a real message to Feishu webhook (manual verification only)."""
    from app.services.notification import send_feishu_notification

    webhook_url = os.environ["FEISHU_WEBHOOK_URL"]
    test_message = "🔔 Price Monitor 测试消息\n⏰ 发送时间: 2026-05-07"

    result = await send_feishu_notification(webhook_url, test_message)

    assert result.get("code") == 0, f"Feishu API error: {result}"
    print(f"✅ Feishu webhook test passed: {result}")


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("FEISHU_WEBHOOK_URL") in (None, "", "skip"),
    reason="FEISHU_WEBHOOK_URL not configured",
)
async def test_feishu_webhook_new_job_notification():
    """Test the new job notification with real webhook."""
    from unittest.mock import MagicMock

    from app.services.notification import send_new_job_notification

    mock_config = MagicMock()
    mock_config.name = "测试搜索配置"

    result = await send_new_job_notification(mock_config, 3, 50)

    # When FEISHU_WEBHOOK_URL is set, it uses that; otherwise checks user.webhook
    assert result.get("code") == 0 or result.get("status") == "skipped", (
        f"Unexpected result: {result}"
    )
    print(f"✅ New job notification test result: {result}")
