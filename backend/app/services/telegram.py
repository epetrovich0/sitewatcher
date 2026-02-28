import logging
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


async def send_telegram_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Send a message via Telegram Bot API."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping alert")
        return False

    url = f"{TELEGRAM_API}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            })
            if resp.status_code == 200:
                return True
            logger.error(f"Telegram API error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def format_alert_down(site_name: str, url: str, error: Optional[str], status_code: Optional[int]) -> str:
    name = site_name or url
    lines = [f"🔴 <b>Site Down</b>: {name}", f"🌐 <code>{url}</code>"]
    if status_code:
        lines.append(f"📊 Status: <b>{status_code}</b>")
    if error:
        lines.append(f"❌ Error: {error}")
    return "\n".join(lines)


def format_alert_recovered(site_name: str, url: str, response_time: float) -> str:
    name = site_name or url
    return (
        f"🟢 <b>Site Recovered</b>: {name}\n"
        f"🌐 <code>{url}</code>\n"
        f"⚡ Response time: <b>{response_time:.2f}s</b>"
    )


def format_alert_slow(site_name: str, url: str, response_time: float, threshold: float) -> str:
    name = site_name or url
    return (
        f"🟡 <b>Slow Response</b>: {name}\n"
        f"🌐 <code>{url}</code>\n"
        f"⏱ Response time: <b>{response_time:.2f}s</b> (threshold: {threshold:.1f}s)"
    )


def format_alert_changed(site_name: str, url: str) -> str:
    name = site_name or url
    return (
        f"🔵 <b>Content Changed</b>: {name}\n"
        f"🌐 <code>{url}</code>\n"
        f"📝 The page content has been updated."
    )


def format_upgrade_message(upgrade_link: str) -> str:
    return (
        "✨ <b>Upgrade to Pro</b>\n\n"
        "You've hit the free tier limit (1 site, checks every 60 min).\n\n"
        "With <b>Pro</b> you get:\n"
        "• Up to <b>50 sites</b>\n"
        "• Checks every <b>1 minute</b>\n"
        "• Content change detection\n"
        "• Priority alerts\n\n"
        f"👉 <a href=\"{upgrade_link}\">Activate Pro</a>"
    )
