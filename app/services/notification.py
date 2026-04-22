"""Feishu webhook notification service."""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


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