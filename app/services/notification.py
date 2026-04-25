"""Feishu webhook notification service."""
from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.database import AsyncSessionLocal


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
)
async def send_feishu_notification(webhook_url: str, message: str) -> dict:
    """Send notification via Feishu webhook.

    Args:
        webhook_url: Feishu webhook URL
        message: Text message to send

    Returns:
        Response from Feishu API

    Raises:
        httpx.HTTPStatusError: If request fails after retries
    """
    if not webhook_url:
        raise ValueError("Feishu webhook URL is required")

    payload = {
        "msg_type": "text",
        "content": {
            "text": message,
        },
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()
        return response.json()


async def send_new_job_notification(
    config: "JobSearchConfig",
    new_job_count: int,
    total_scraped: int,
) -> dict:
    """Send Feishu notification for newly discovered jobs.

    Args:
        config: The JobSearchConfig that was crawled
        new_job_count: Number of new jobs found
        total_scraped: Total number of jobs scraped this run

    Returns:
        Response from Feishu API
    """
    from app.models.user import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        user_result = await db.execute(select(User).where(User.id == 1))
        user = user_result.scalar_one_or_none()

    if not user or not user.feishu_webhook_url:
        return {"status": "skipped", "reason": "no_webhook"}

    message = f"""🔔 Boss直聘新职位提醒

搜索配置：{config.name}
本次发现 {new_job_count} 个新职位（共扫描 {total_scraped} 个）

---
共收录职位请查看管理后台"""

    return await send_feishu_notification(user.feishu_webhook_url, message)
