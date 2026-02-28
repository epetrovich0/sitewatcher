import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, and_
from app.db.database import AsyncSessionLocal
from app.models.site import Site
from app.models.user import User
from app.models.check import CheckLog
from app.services.checker import check_site
from app.services.telegram import (
    send_telegram_message,
    format_alert_down,
    format_alert_recovered,
    format_alert_slow,
    format_alert_changed,
)

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def run_checks():
    """Main scheduler job: find due sites and check them."""
    now = datetime.utcnow()
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Site).where(
                and_(
                    Site.is_active == True,
                    (Site.next_check_at == None) | (Site.next_check_at <= now),
                )
            )
        )
        sites = result.scalars().all()

    for site in sites:
        try:
            await process_site_check(site.id)
        except Exception as e:
            logger.error(f"Error checking site {site.id}: {e}")


async def process_site_check(site_id: int):
    async with AsyncSessionLocal() as db:
        site = await db.get(Site, site_id)
        if not site:
            return

        user_result = await db.execute(select(User).where(User.id == site.user_id))
        user = user_result.scalar_one_or_none()

        check_result = await check_site(site.url)

        is_up = check_result["is_up"]
        response_time = check_result["response_time"]
        content_hash = check_result["content_hash"]
        error_message = check_result["error_message"]
        status_code = check_result["status_code"]

        prev_status = site.last_status
        prev_hash = site.last_content_hash

        # Determine alert type
        alert_type = None
        alert_text = None

        if not is_up and prev_status != "down":
            alert_type = "down"
            if user and user.telegram_chat_id and site.alert_on_down:
                alert_text = format_alert_down(site.name, site.url, error_message, status_code)

        elif is_up and prev_status == "down":
            alert_type = "recovered"
            if user and user.telegram_chat_id:
                alert_text = format_alert_recovered(site.name, site.url, response_time or 0)

        elif is_up and site.monitor_response_time and site.alert_on_slow:
            if response_time and response_time > site.response_time_threshold:
                alert_type = "slow"
                if user and user.telegram_chat_id:
                    alert_text = format_alert_slow(
                        site.name, site.url, response_time, site.response_time_threshold
                    )

        content_changed = False
        if is_up and site.monitor_content_changes and prev_hash and content_hash:
            if prev_hash != content_hash:
                content_changed = True
                if not alert_type and site.alert_on_change and user and user.telegram_chat_id:
                    alert_type = "changed"
                    alert_text = format_alert_changed(site.name, site.url)

        # Send alert
        alert_sent = False
        if alert_text and user and user.telegram_chat_id:
            alert_sent = await send_telegram_message(user.telegram_chat_id, alert_text)

        # Log the check
        log = CheckLog(
            site_id=site.id,
            is_up=is_up,
            status_code=status_code,
            response_time=response_time,
            error_message=error_message,
            content_changed=content_changed,
            content_hash=content_hash,
            alert_sent=alert_sent,
            alert_type=alert_type,
        )
        db.add(log)

        # Update site state
        site.last_status = "up" if is_up else "down"
        site.last_response_time = response_time
        site.last_content_hash = content_hash
        site.last_checked_at = datetime.utcnow()
        site.next_check_at = datetime.utcnow() + timedelta(minutes=site.check_interval)

        await db.commit()


def start_scheduler():
    scheduler.add_job(run_checks, "interval", minutes=1, id="site_checks", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    scheduler.shutdown()
