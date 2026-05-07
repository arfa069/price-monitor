"""Tests for notification service."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSendFeishuNotification:
    """Tests for send_feishu_notification."""

    @pytest.mark.asyncio
    async def test_send_notification_success(self):
        """Successful webhook call returns response JSON."""
        from app.services.notification import send_feishu_notification

        mock_response = MagicMock()
        mock_response.json.return_value = {"code": 0, "msg": "ok"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await send_feishu_notification(
                "https://open.feishu.cn/hook/test", "Hello"
            )

        assert result == {"code": 0, "msg": "ok"}
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://open.feishu.cn/hook/test"
        assert call_args[1]["json"]["msg_type"] == "text"
        assert call_args[1]["json"]["content"]["text"] == "Hello"

    @pytest.mark.asyncio
    async def test_send_notification_empty_url_raises(self):
        """Empty webhook URL raises after retries exhausted."""
        from tenacity import RetryError

        from app.services.notification import send_feishu_notification

        with pytest.raises(RetryError):
            await send_feishu_notification("", "Hello")

    @pytest.mark.asyncio
    async def test_send_notification_http_error(self):
        """HTTP error raises after retries exhausted."""
        from app.services.notification import send_feishu_notification

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 400")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception):
                await send_feishu_notification(
                    "https://open.feishu.cn/hook/test", "Hello"
                )


class TestSendNewJobNotification:
    """Tests for send_new_job_notification."""

    @pytest.mark.asyncio
    async def test_send_new_job_notification_success(self):
        """User with webhook gets notification sent."""
        from app.services.notification import send_new_job_notification

        mock_config = MagicMock()
        mock_config.name = "Python 后端"

        with patch(
            "app.services.notification.get_cached_user_config",
            new_callable=AsyncMock,
        ) as mock_get_config:
            mock_get_config.return_value = {
                "feishu_webhook_url": "https://open.feishu.cn/hook/test",
            }
            with patch(
                "app.services.notification.send_feishu_notification",
                new_callable=AsyncMock,
            ) as mock_send:
                mock_send.return_value = {"code": 0, "msg": "ok"}
                result = await send_new_job_notification(mock_config, 5, 100)

        assert result == {"code": 0, "msg": "ok"}
        mock_send.assert_called_once()
        call_message = mock_send.call_args[0][1]
        assert "Python 后端" in call_message
        assert "5" in call_message
        assert "100" in call_message

    @pytest.mark.asyncio
    async def test_send_new_job_notification_no_webhook_skips(self):
        """User without webhook returns skipped status."""
        from app.services.notification import send_new_job_notification

        mock_config = MagicMock()
        mock_config.name = "Python 后端"

        with patch(
            "app.services.notification.get_cached_user_config",
            new_callable=AsyncMock,
        ) as mock_get_config:
            mock_get_config.return_value = {"feishu_webhook_url": ""}
            result = await send_new_job_notification(mock_config, 5, 100)

        assert result["status"] == "skipped"
        assert "no_webhook" in result["reason"]

    @pytest.mark.asyncio
    async def test_send_new_job_notification_no_user_skips(self):
        """No user found returns skipped status."""
        from app.services.notification import send_new_job_notification

        mock_config = MagicMock()
        mock_config.name = "Python 后端"

        with patch(
            "app.services.notification.get_cached_user_config",
            new_callable=AsyncMock,
        ) as mock_get_config:
            mock_get_config.return_value = None
            result = await send_new_job_notification(mock_config, 5, 100)

        assert result["status"] == "skipped"
        assert "no_webhook" in result["reason"]
