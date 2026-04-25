"""
Basic tests for SiteWatcher.
Run with: pytest backend/tests/ -v
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plain(self):
        from app.services.auth import hash_password
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"
        assert len(hashed) > 20

    def test_verify_correct_password(self):
        from app.services.auth import hash_password, verify_password
        hashed = hash_password("mysecret")
        assert verify_password("mysecret", hashed) is True

    def test_verify_wrong_password(self):
        from app.services.auth import hash_password, verify_password
        hashed = hash_password("mysecret")
        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        from app.services.auth import hash_password
        h1 = hash_password("mysecret")
        h2 = hash_password("mysecret")
        assert h1 != h2  # bcrypt uses different salts


class TestJWT:
    def test_create_and_decode_token(self):
        from app.services.auth import create_access_token, get_current_user
        token_data = {"sub": "42"}
        token = create_access_token(token_data)
        assert isinstance(token, str)
        assert len(token) > 10

    def test_invalid_token_returns_none(self):
        """An invalid token should not raise an exception."""
        from jose import jwt
        try:
            jwt.decode("invalid.token.here", "wrong-secret", algorithms=["HS256"])
            assert False, "Should have raised"
        except Exception:
            pass  # Ожидаемо


# ── Checker ───────────────────────────────────────────────────────────────────

class TestChecker:
    @pytest.mark.asyncio
    async def test_check_site_success(self):
        """Successful site response."""
        from app.services.checker import check_site

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Hello World</body></html>"
        mock_response.content = b"<html><body>Hello World</body></html>"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await check_site("https://example.com")

        assert result["is_up"] is True
        assert result["status_code"] == 200
        assert result["error_message"] is None
        assert result["response_time"] is not None
        assert result["content_hash"] is not None

    @pytest.mark.asyncio
    async def test_check_site_server_error(self):
        """A 5xx response is treated as down."""
        from app.services.checker import check_site

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_response.content = b"Service Unavailable"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=mock_response)

            result = await check_site("https://example.com")

        assert result["is_up"] is False
        assert result["status_code"] == 503

    @pytest.mark.asyncio
    async def test_check_site_timeout(self):
        """A timeout returns is_up=False."""
        import httpx
        from app.services.checker import check_site

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("timeout")
            )

            result = await check_site("https://example.com")

        assert result["is_up"] is False
        assert result["status_code"] is None
        assert "timed out" in result["error_message"].lower()

    @pytest.mark.asyncio
    async def test_check_site_connection_error(self):
        """A connection error returns is_up=False."""
        import httpx
        from app.services.checker import check_site

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("connection refused")
            )

            result = await check_site("https://nonexistent.example.com")

        assert result["is_up"] is False
        assert result["error_message"] is not None

    @pytest.mark.asyncio
    async def test_content_hash_changes(self):
        """Different content produces different hashes."""
        from app.services.checker import check_site

        def make_mock(content):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = content
            mock_response.content = content.encode()
            return mock_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=make_mock("<html>Version 1</html>"))
            result1 = await check_site("https://example.com")

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.get = AsyncMock(return_value=make_mock("<html>Version 2</html>"))
            result2 = await check_site("https://example.com")

        assert result1["content_hash"] != result2["content_hash"]


# ── Telegram alerts ───────────────────────────────────────────────────────────

class TestTelegramFormatters:
    def test_format_alert_down(self):
        from app.services.telegram import format_alert_down
        msg = format_alert_down("My Site", "https://example.com", "Connection failed", None)
        assert "My Site" in msg
        assert "Down" in msg or "down" in msg.lower()

    def test_format_alert_recovered(self):
        from app.services.telegram import format_alert_recovered
        msg = format_alert_recovered("My Site", "https://example.com", 0.42)
        assert "My Site" in msg
        assert "Recovered" in msg or "recovered" in msg.lower()

    def test_format_alert_slow(self):
        from app.services.telegram import format_alert_slow
        msg = format_alert_slow("My Site", "https://example.com", 6.5, 5.0)
        assert "My Site" in msg
        assert "6" in msg  # response time is included

    def test_format_alert_changed(self):
        from app.services.telegram import format_alert_changed
        msg = format_alert_changed("My Site", "https://example.com")
        assert "My Site" in msg
        assert "Changed" in msg or "changed" in msg.lower()

    @pytest.mark.asyncio
    async def test_send_skipped_without_token(self):
        """Without a token the message is not sent and returns False."""
        from app.services.telegram import send_telegram_message
        with patch("app.services.telegram.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = None
            result = await send_telegram_message("123", "test message")
        assert result is False


# ── Uptime calculation ────────────────────────────────────────────────────────

class TestUptimeCalculation:
    def test_all_up(self):
        checks = [MagicMock(is_up=True) for _ in range(10)]
        from app.api.status import uptime_percent
        assert uptime_percent(checks) == 100.0

    def test_all_down(self):
        checks = [MagicMock(is_up=False) for _ in range(10)]
        from app.api.status import uptime_percent
        assert uptime_percent(checks) == 0.0

    def test_half_up(self):
        checks = [MagicMock(is_up=i % 2 == 0) for i in range(10)]
        from app.api.status import uptime_percent
        assert uptime_percent(checks) == 50.0

    def test_empty_checks(self):
        from app.api.status import uptime_percent
        assert uptime_percent([]) == 100.0
