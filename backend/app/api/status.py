"""
Public status page — no auth required.
GET /api/status/{username}  →  public uptime page for a user's sites
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.db.database import get_db
from app.models.user import User
from app.models.site import Site
from app.models.check import CheckLog

router = APIRouter(prefix="/status", tags=["status"])


def uptime_percent(checks: list) -> float:
    if not checks:
        return 100.0
    up = sum(1 for c in checks if c.is_up)
    return round(up / len(checks) * 100, 1)


@router.get("/{username}")
async def public_status(username: str, db: AsyncSession = Depends(get_db)):
    """
    Public status page for a user's monitored sites.
    Returns uptime stats for the last 30 days.
    No authentication required.
    """
    # Find the user by telegram_username or email prefix
    result = await db.execute(
        select(User).where(User.telegram_username == username)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Status page not found")

    # Get active sites
    sites_result = await db.execute(
        select(Site).where(Site.user_id == user.id, Site.is_active == True)
    )
    sites = sites_result.scalars().all()

    since = datetime.utcnow() - timedelta(days=30)
    output = []

    for site in sites:
        # Last 90 checks for the chart (last 90 points)
        checks_result = await db.execute(
            select(CheckLog)
            .where(CheckLog.site_id == site.id, CheckLog.checked_at >= since)
            .order_by(CheckLog.checked_at.asc())
        )
        checks = checks_result.scalars().all()

        # Last 24 hours separately
        since_24h = datetime.utcnow() - timedelta(hours=24)
        checks_24h = [c for c in checks if c.checked_at >= since_24h]

        output.append({
            "name": site.name or site.url,
            "url": site.url,
            "status": site.last_status or "unknown",
            "last_checked": site.last_checked_at.isoformat() if site.last_checked_at else None,
            "last_response_time": site.last_response_time,
            "uptime_30d": uptime_percent(checks),
            "uptime_24h": uptime_percent(checks_24h),
            # Last 30 points for the mini chart
            "history": [
                {
                    "time": c.checked_at.isoformat(),
                    "is_up": c.is_up,
                    "response_ms": round(c.response_time * 1000) if c.response_time else None,
                }
                for c in checks[-30:]
            ],
        })

    # Overall page status
    all_up = all(s["status"] == "up" for s in output)
    any_down = any(s["status"] == "down" for s in output)

    return {
        "username": username,
        "overall": "operational" if all_up else ("partial_outage" if any_down else "unknown"),
        "generated_at": datetime.utcnow().isoformat(),
        "sites": output,
    }
