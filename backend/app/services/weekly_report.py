"""
Weekly AI summary job — runs every Monday at 09:00 UTC.
Collects stats for each user's sites and sends a Telegram report.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from app.db.database import AsyncSessionLocal
from app.models.user import User
from app.models.site import Site
from app.models.check import CheckLog
from app.services.telegram import send_telegram_message
from app.services.ai_analysis import generate_weekly_summary, generate_full_weekly_report

logger = logging.getLogger(__name__)


async def _get_site_week_stats(db, site_id: int) -> dict:
    """Compute uptime stats for a site over the last 7 days."""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    # This week's checks
    result = await db.execute(
        select(CheckLog).where(
            and_(CheckLog.site_id == site_id, CheckLog.checked_at >= week_ago)
        ).order_by(CheckLog.checked_at.asc())
    )
    checks = result.scalars().all()

    # Last week's checks (for comparison)
    result_prev = await db.execute(
        select(CheckLog).where(
            and_(
                CheckLog.site_id == site_id,
                CheckLog.checked_at >= two_weeks_ago,
                CheckLog.checked_at < week_ago,
            )
        )
    )
    prev_checks = result_prev.scalars().all()

    if not checks:
        return {}

    total = len(checks)
    up_count = sum(1 for c in checks if c.is_up)
    uptime_pct = up_count / total * 100

    resp_times = [c.response_time for c in checks if c.response_time and c.is_up]
    avg_response_ms = (sum(resp_times) / len(resp_times) * 1000) if resp_times else 0

    prev_resp = [c.response_time for c in prev_checks if c.response_time and c.is_up]
    prev_avg_ms = (sum(prev_resp) / len(prev_resp) * 1000) if prev_resp else None

    # Detect incident windows (consecutive down checks)
    incidents = []
    in_incident = False
    incident_start = None
    incident_error = None
    for c in checks:
        if not c.is_up and not in_incident:
            in_incident = True
            incident_start = c.checked_at
            incident_error = c.error_message
        elif c.is_up and in_incident:
            duration = int((c.checked_at - incident_start).total_seconds() / 60)
            incidents.append({
                "time": incident_start,
                "duration_min": duration,
                "error": incident_error,
            })
            in_incident = False
    if in_incident:
        duration = int((datetime.utcnow() - incident_start).total_seconds() / 60)
        incidents.append({"time": incident_start, "duration_min": duration, "error": incident_error})

    return {
        "total_checks": total,
        "uptime_pct": uptime_pct,
        "incidents": len(incidents),
        "avg_response_ms": avg_response_ms,
        "prev_avg_response_ms": prev_avg_ms,
        "incident_log": incidents,
    }


async def send_weekly_reports():
    """Main job: send weekly AI summaries to all users with Telegram connected."""
    logger.info("Starting weekly report job")
    async with AsyncSessionLocal() as db:
        # Get all users with Telegram connected
        result = await db.execute(
            select(User).where(User.telegram_chat_id.isnot(None), User.is_active == True)
        )
        users = result.scalars().all()

    for user in users:
        try:
            await _send_user_weekly_report(user)
        except Exception as e:
            logger.error(f"Weekly report failed for user {user.id}: {e}")

    logger.info(f"Weekly reports sent to {len(users)} users")


async def _send_user_weekly_report(user: User):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Site).where(Site.user_id == user.id, Site.is_active == True)
        )
        sites = result.scalars().all()

    if not sites:
        return

    sites_data = []
    for site in sites:
        async with AsyncSessionLocal() as db:
            stats = await _get_site_week_stats(db, site.id)
        if stats:
            stats["site_name"] = site.name or site.url
            stats["url"] = site.url
            sites_data.append(stats)

    if not sites_data:
        return

    header = "📊 <b>Weekly Report</b>\n\n"

    if len(sites_data) == 1:
        s = sites_data[0]
        ai_text = await generate_weekly_summary(
            site_name=s["site_name"],
            site_url=s["url"],
            stats=s,
            incident_log=s.get("incident_log", []),
        )
        body = ai_text or _fallback_single_site(s)
    else:
        ai_text = await generate_full_weekly_report(
            user_email=user.email,
            sites_data=sites_data,
        )
        if not ai_text:
            # Fallback: simple per-site list
            lines = [f"• <b>{s['site_name']}</b>: {s['uptime_pct']:.1f}% uptime, {s['incidents']} incidents" for s in sites_data]
            ai_text = "\n".join(lines)
        body = ai_text

    message = header + body
    await send_telegram_message(user.telegram_chat_id, message)
    logger.info(f"Weekly report sent to user {user.id}")


def _fallback_single_site(s: dict) -> str:
    """Plain text fallback when AI is unavailable."""
    lines = [
        f"<b>{s['site_name']}</b>",
        f"Uptime: {s['uptime_pct']:.1f}% over 7 days",
        f"Incidents: {s['incidents']}",
        f"Avg response: {s['avg_response_ms']:.0f}ms",
    ]
    if s.get("incident_log"):
        lines.append("\nIncidents:")
        for inc in s["incident_log"][:3]:
            t = inc["time"]
            lines.append(f"  • {t.strftime('%b %d %H:%M')}: {inc.get('error', 'down')} ({inc.get('duration_min', '?')} min)")
    return "\n".join(lines)
