"""
Upgrade endpoint stub.
In production, replace with real payment processor (Stripe, LiqPay, etc.)
For demo: a secret token activates Pro for the user.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db.database import get_db
from app.models.user import User
from app.api.auth import get_current_active_user
from app.services.telegram import send_telegram_message

router = APIRouter(prefix="/billing", tags=["billing"])


class ActivateProRequest(BaseModel):
    # In prod: payment_intent_id or webhook payload
    # For demo: just the user's upgrade_token
    upgrade_token: str


@router.post("/activate-pro")
async def activate_pro(
    req: ActivateProRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Demo endpoint to activate Pro.
    In production: verify payment with Stripe/etc. webhook before setting is_paid=True.
    """
    result = await db.execute(select(User).where(User.upgrade_token == req.upgrade_token))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    if not user.is_paid:
        user.is_paid = True
        await db.commit()

        # Notify via Telegram
        if user.telegram_chat_id:
            await send_telegram_message(
                user.telegram_chat_id,
                "🎉 <b>Pro activated!</b>\n\n"
                "You now have access to:\n"
                "• Up to 50 monitored sites\n"
                "• Checks every 1 minute\n"
                "• Content change monitoring\n\n"
                "Thank you for upgrading! 🚀",
            )

    return {"ok": True, "is_paid": user.is_paid, "email": user.email}


@router.get("/status")
async def billing_status(user: User = Depends(get_current_active_user)):
    return {
        "is_paid": user.is_paid,
        "upgrade_token": user.upgrade_token,
    }
