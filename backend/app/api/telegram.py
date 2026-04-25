"""
Telegram webhook handler.
- Standard commands: /start, /status, /upgrade, /help, /sites
- AI chat (Pro): any text is analyzed and answered
- Site creation through the bot is available on Pro
"""
import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.site import Site
from app.models.check import CheckLog
from app.services.telegram import send_telegram_message
from app.services.ai_analysis import handle_bot_chat
from app.services.scheduler import process_site_check
from app.core.config import settings
from app.api.sites import site_to_dict
from datetime import datetime, timedelta
from sqlalchemy import delete as sql_delete

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

# ── Help texts ────────────────────────────────────────────────────────────────

BOT_COMMANDS_HELP_RU = """
<b>SiteWatcher commands</b>

/start — Link Telegram to your account
/sites — List your sites
/status — Account status
/upgrade — Upgrade to Pro
/help — This help

<i>Pro: just write to the bot in natural language — it understands!</i>
Examples: "show stats", "add site example.com", "how is my site doing?"
"""

BOT_COMMANDS_HELP_EN = """
<b>SiteWatcher bot commands</b>

/start — Link your Telegram account
/sites — List your monitored sites
/status — Show account status
/upgrade — Get Pro upgrade link
/help — Show this message

<i>Pro: just write in natural language — the bot understands!</i>
Examples: "show stats", "add site example.com", "how is my site doing?"
"""


def _detect_lang(text: str) -> str:
    """Rough language detection based on Cyrillic characters."""
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04ff')
    return "ru" if cyrillic > len(text) * 0.2 else "en"


# ── Data helpers ─────────────────────────────────────────────────────────────

async def _get_user_sites(db: AsyncSession, user_id: int) -> list[dict]:
    result = await db.execute(select(Site).where(Site.user_id == user_id))
    return [site_to_dict(s) for s in result.scalars().all()]


async def _get_quick_stats(db: AsyncSession, user_id: int) -> dict:
    """7-day statistics across all of the user's sites."""
    week_ago = datetime.utcnow() - timedelta(days=7)
    sites_result = await db.execute(
        select(Site).where(Site.user_id == user_id, Site.is_active == True)
    )
    sites = sites_result.scalars().all()

    total_checks = 0
    total_up = 0
    total_incidents = 0

    for site in sites:
        checks_result = await db.execute(
            select(CheckLog).where(
                CheckLog.site_id == site.id,
                CheckLog.checked_at >= week_ago,
            )
        )
        checks = checks_result.scalars().all()
        total_checks += len(checks)
        total_up += sum(1 for c in checks if c.is_up)
        # Count up→down transitions as incidents
        prev_up = True
        for c in checks:
            if not c.is_up and prev_up:
                total_incidents += 1
            prev_up = c.is_up

    avg_uptime = (total_up / total_checks * 100) if total_checks else 100.0
    return {
        "avg_uptime": avg_uptime,
        "total_incidents": total_incidents,
        "total_checks": total_checks,
    }


# ── Site list formatting ─────────────────────────────────────────────────────

def _format_sites_message(sites: list[dict], lang: str = "ru") -> str:
    if not sites:
        return (
            "You do not have any sites yet. Add your first one:\n<code>add site https://example.com</code>"
            if lang == "ru" else
            "No sites yet. Add your first:\n<code>add site https://example.com</code>"
        )

    lines = []
    for s in sites:
        emoji = {"up": "🟢", "down": "🔴", "unknown": "⚪"}.get(s.get("last_status", "unknown"), "⚪")
        rt = f"{s['last_response_time']:.2f}s" if s.get("last_response_time") else "—"
        paused = " ⏸" if not s.get("is_active") else ""
        lines.append(f"{emoji} <b>{s['name']}</b>{paused}")
        lines.append(f"   <code>{s['url']}</code>  ⚡{rt}  ⏱{s['check_interval']}min")

    header = f"📡 <b>Your sites ({len(sites)})</b>\n\n"
    return header + "\n".join(lines)


# ── Add a site through the bot ────────────────────────────────────────────────

async def _bot_add_site(user: User, url: str, name: str, db: AsyncSession) -> str:
    from app.models.site import Site as SiteModel

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Check the site limit
    count_result = await db.execute(
        select(func.count(SiteModel.id)).where(SiteModel.user_id == user.id)
    )
    count = count_result.scalar()
    max_sites = settings.PAID_TIER_MAX_SITES if user.is_paid else settings.FREE_TIER_MAX_SITES

    if count >= max_sites:
        if not user.is_paid:
            upgrade_url = f"{settings.FRONTEND_URL}/upgrade?token={user.upgrade_token}"
            return (
                f"❌ Free plan limit reached (1 site).\n\n"
                f"👉 <a href=\"{upgrade_url}\">Upgrade to Pro</a> — up to 50 sites, checks every minute."
            )
        return f"❌ Maximum sites reached ({max_sites})."

    min_interval = settings.PAID_TIER_MIN_INTERVAL if user.is_paid else settings.FREE_TIER_MIN_INTERVAL

    site = SiteModel(
        user_id=user.id,
        url=url,
        name=name or url,
        check_interval=min_interval if user.is_paid else 60,
        monitor_availability=True,
        monitor_response_time=True,
        monitor_content_changes=False,
        response_time_threshold=5.0,
        alert_on_down=True,
        alert_on_slow=True,
        alert_on_change=True,
        last_status="unknown",
    )
    db.add(site)
    await db.commit()
    await db.refresh(site)

    # Run the initial check immediately
    try:
        await process_site_check(site.id)
    except Exception as e:
        logger.error(f"Initial check failed for site {site.id}: {e}")

    interval_str = f"{min_interval} min" if user.is_paid else "60 min"
    return (
        f"✅ <b>Site added!</b>\n\n"
        f"🌐 <code>{url}</code>\n"
        f"📛 Name: {name or url}\n"
        f"⏱ Checks every {interval_str}\n\n"
        f"The first check is already running — you will see the result soon."
    )


async def _bot_delete_site(user: User, site_id: int, db: AsyncSession) -> str:
    site = await db.get(Site, site_id)
    if not site or site.user_id != user.id:
        return "❌ Site not found."

    site_name = site.name or site.url
    await db.execute(sql_delete(CheckLog).where(CheckLog.site_id == site_id))
    await db.delete(site)
    await db.commit()
    return f"🗑 Site <b>{site_name}</b> deleted."


# ── Main handler ─────────────────────────────────────────────────────────────

async def handle_telegram_update(update: dict, db: AsyncSession):
    # Handle pre_checkout_query (Stars payment)
    pre_checkout = update.get("pre_checkout_query")
    if pre_checkout:
        await _handle_pre_checkout(pre_checkout)
        return

    # Handle successful_payment
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    # Stars: successful_payment is inside message
    if message.get("successful_payment"):
        await _handle_successful_payment(message, db)
        return

    chat_id = str(message["chat"]["id"])
    text = message.get("text", "").strip()
    username = message.get("from", {}).get("username", "")
    lang = _detect_lang(text)

    # ── /start ────────────────────────────────────────────────────────────────
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        token = parts[1].strip() if len(parts) > 1 else None

        if token:
            result = await db.execute(select(User).where(User.upgrade_token == token))
            user = result.scalar_one_or_none()
            if user:
                user.telegram_chat_id = chat_id
                user.telegram_username = username
                await db.commit()
                await send_telegram_message(
                    chat_id,
                    f"✅ <b>Account linked!</b>\n\n"
                    f"Telegram is connected to <b>{user.email}</b>.\n"
                    f"Alerts will arrive here.\n\n"
                    + BOT_COMMANDS_HELP_RU,
                )
            else:
                await send_telegram_message(
                    chat_id,
                    "❌ Invalid or expired link. Create a new one in the app settings."
                )
        else:
            await send_telegram_message(
                chat_id,
                "👋 <b>Welcome to SiteWatcher!</b>\n\n"
                "To link your account, open Settings in the app and click <b>Connect Telegram</b>.\n\n"
                + BOT_COMMANDS_HELP_RU,
            )
        return

    # All other commands require an authenticated user
    user_result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
    user = user_result.scalar_one_or_none()

    # ── /status ───────────────────────────────────────────────────────────────
    if text == "/status":
        if not user:
            await send_telegram_message(chat_id, "❌ Account is not linked. Use /start with the link from the app.")
            return
        tier = "⭐ Pro" if user.is_paid else "🆓 Free"
        sites = await _get_user_sites(db, user.id)
        up = sum(1 for s in sites if s["last_status"] == "up")
        down = sum(1 for s in sites if s["last_status"] == "down")
        await send_telegram_message(
            chat_id,
            f"👤 <b>Your account</b>\n\n"
            f"Email: {user.email}\n"
            f"Plan: {tier}\n"
            f"Sites: {len(sites)} (🟢{up} 🔴{down})\n"
            f"Alerts: ✅ active",
        )
        return

    # ── /sites ────────────────────────────────────────────────────────────────
    if text == "/sites":
        if not user:
            await send_telegram_message(chat_id, "❌ Account is not linked.")
            return
        sites = await _get_user_sites(db, user.id)
        await send_telegram_message(chat_id, _format_sites_message(sites, lang))
        return

    # ── /upgrade ──────────────────────────────────────────────────────────────
    if text == "/upgrade":
        if not user:
            await send_telegram_message(chat_id, "❌ Account is not linked.")
            return
        if user.is_paid:
            await send_telegram_message(chat_id, "⭐ You are already on Pro!")
            return
        upgrade_url = f"{settings.FRONTEND_URL}/upgrade?token={user.upgrade_token}"
        await send_telegram_message(
            chat_id,
            f"✨ <b>Upgrade to Pro</b>\n\n"
            f"• Up to 50 sites\n"
            f"• Checks every minute\n"
            f"• Content change monitoring\n"
            f"• AI analysis in chat\n\n"
            f"👉 <a href=\"{upgrade_url}\">Upgrade to Pro</a>",
        )
        return

    # ── /help ─────────────────────────────────────────────────────────────────
    if text == "/help":
        help_text = BOT_COMMANDS_HELP_EN
        await send_telegram_message(chat_id, help_text)
        return

    # ── Everything else: AI chat ─────────────────────────────────────────────
    if not user:
        await send_telegram_message(
            chat_id,
            "❌ Account is not linked.\n\nUse /start with the link from the app."
        )
        return

    # AI chat is Pro only
    if not user.is_paid:
        upgrade_url = f"{settings.FRONTEND_URL}/upgrade?token={user.upgrade_token}"
        await send_telegram_message(
            chat_id,
            "🤖 <b>AI assistant is available in Pro</b>\n\n"
            "Ask the bot any question in natural language:\n"
            '"show stats", "add site", "what happened yesterday?"\n\n'
            f"👉 <a href=\"{upgrade_url}\">Upgrade to Pro</a>\n\n"
            "For now use the commands: /sites /status /help"
        )
        return

    # Send typing indicator
    await _send_typing(chat_id)

    # Collect context
    sites = await _get_user_sites(db, user.id)
    stats = await _get_quick_stats(db, user.id)

    reply, action = await handle_bot_chat(
        user_message=text,
        user=user,
        sites=sites,
        stats=stats,
    )

    # Execute action if any
    if action:
        if action["type"] == "add_site" and action.get("url"):
            action_reply = await _bot_add_site(user, action["url"], action.get("name", ""), db)
            await send_telegram_message(chat_id, reply)
            await send_telegram_message(chat_id, action_reply)
            return
        elif action["type"] == "delete_site" and action.get("id"):
            action_reply = await _bot_delete_site(user, action["id"], db)
            await send_telegram_message(chat_id, reply)
            await send_telegram_message(chat_id, action_reply)
            return

    await send_telegram_message(chat_id, reply)


async def _send_typing(chat_id: str):
    """Send chatAction=typing."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
            )
    except Exception:
        pass


async def _handle_pre_checkout(pre_checkout: dict):
    """Confirm the pre_checkout_query for Telegram Stars."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerPreCheckoutQuery",
                json={"pre_checkout_query_id": pre_checkout["id"], "ok": True},
            )
    except Exception as e:
        logger.error(f"pre_checkout_query error: {e}")


async def _handle_successful_payment(message: dict, db: AsyncSession):
    """Activate Pro after a successful Telegram Stars payment."""
    chat_id = str(message["chat"]["id"])
    payment = message["successful_payment"]
    payload = payment.get("invoice_payload", "")

    result = await db.execute(select(User).where(User.upgrade_token == payload))
    user = result.scalar_one_or_none()

    if user and not user.is_paid:
        user.is_paid = True
        await db.commit()
        from app.services.telegram import send_telegram_message as send_msg
        await send_msg(
            chat_id,
            "🎉 <b>Pro activated!</b>\n\n"
            "You now have:\n"
            "• Up to 50 sites\n"
            "• Checks every minute\n"
            "• Content change monitoring\n"
            "• AI assistant in Telegram\n\n"
            "Thank you! 🚀"
        )
    else:
        logger.warning(f"Stars payment: user not found or already Pro, payload={payload}")


# ── FastAPI routes ────────────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        update = await request.json()
        await handle_telegram_update(update, db)
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}", exc_info=True)
    return {"ok": True}


@router.get("/link-url")
async def get_link_url(token: str, db: AsyncSession = Depends(get_db)):
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