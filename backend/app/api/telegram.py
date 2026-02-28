import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.user import User
from app.services.telegram import send_telegram_message
from app.core.config import settings

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

BOT_COMMANDS_HELP = """
<b>SiteWatcher Bot Commands</b>

/start — Link your Telegram account
/status — Show your account status
/upgrade — Get Pro upgrade link
/help — Show this message
"""


async def handle_telegram_update(update: dict, db: AsyncSession):
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = str(message["chat"]["id"])
    text = message.get("text", "").strip()
    username = message.get("from", {}).get("username", "")

    # Handle /start with token: /start <upgrade_token>
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        token = parts[1].strip() if len(parts) > 1 else None

        if token:
            # Link Telegram to account
            result = await db.execute(select(User).where(User.upgrade_token == token))
            user = result.scalar_one_or_none()
            if user:
                user.telegram_chat_id = chat_id
                user.telegram_username = username
                await db.commit()
                await send_telegram_message(
                    chat_id,
                    f"✅ <b>Account linked!</b>\n\nYour Telegram is now connected to <b>{user.email}</b>.\n"
                    f"You'll receive alerts here.\n\nUse /upgrade to go Pro.",
                )
                return
            else:
                await send_telegram_message(chat_id, "❌ Invalid or expired link. Please generate a new one from the app.")
                return

        await send_telegram_message(
            chat_id,
            "👋 <b>Welcome to SiteWatcher!</b>\n\n"
            "To link your account, go to the app settings and click <b>Connect Telegram</b>.\n\n"
            + BOT_COMMANDS_HELP,
        )
        return

    if text == "/status":
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalar_one_or_none()
        if not user:
            await send_telegram_message(chat_id, "❌ Account not linked. Use /start with a link from the app.")
            return
        tier = "⭐ Pro" if user.is_paid else "🆓 Free"
        await send_telegram_message(
            chat_id,
            f"👤 <b>Your Account</b>\n\n"
            f"Email: {user.email}\n"
            f"Plan: {tier}\n"
            f"Alerts: ✅ Active",
        )
        return

    if text == "/upgrade":
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalar_one_or_none()
        if not user:
            await send_telegram_message(chat_id, "❌ Account not linked.")
            return
        if user.is_paid:
            await send_telegram_message(chat_id, "⭐ You already have Pro!")
            return
        upgrade_url = f"{settings.FRONTEND_URL}/upgrade?token={user.upgrade_token}"
        await send_telegram_message(
            chat_id,
            f"✨ <b>Upgrade to Pro</b>\n\n"
            f"• Up to 50 sites\n"
            f"• Checks every 1 minute\n"
            f"• Content change detection\n\n"
            f"👉 <a href=\"{upgrade_url}\">Upgrade Now</a>",
        )
        return

    if text == "/help":
        await send_telegram_message(chat_id, BOT_COMMANDS_HELP)
        return

    await send_telegram_message(chat_id, "Use /help to see available commands.")


@router.post("/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        update = await request.json()
        await handle_telegram_update(update, db)
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
    return {"ok": True}


@router.get("/link-url")
async def get_link_url(token: str, db: AsyncSession = Depends(get_db)):
    """Returns the Telegram deep link URL for account linking."""
    result = await db.execute(select(User).where(User.upgrade_token == token))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Token not found")

    bot_username = await get_bot_username()
    if not bot_username:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")

    return {
        "link": f"https://t.me/{bot_username}?start={token}",
        "bot_username": bot_username,
    }


async def get_bot_username() -> str | None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
            )
            data = resp.json()
            return data.get("result", {}).get("username")
    except Exception:
        return None
