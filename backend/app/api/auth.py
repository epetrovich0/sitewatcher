from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from app.db.database import get_db
from app.models.user import User
from app.services.auth import (
    hash_password, authenticate_user, create_access_token,
    get_user_by_email, get_current_user, generate_upgrade_token,
    generate_unique_referral_code, get_user_by_referral_code, get_max_sites_for_user
)
from app.core.config import settings
from app.services.telegram import send_telegram_message

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ApplyReferralRequest(BaseModel):
    code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await get_current_user(credentials.credentials, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return user

@router.post("/me/test-alert")
async def test_alert(user: User = Depends(get_current_active_user)):
    if not user.telegram_chat_id:
        raise HTTPException(status_code=400, detail="No telegram_chat_id set")
    result = await send_telegram_message(
        user.telegram_chat_id,
        "🧪 <b>Test alert from SiteWatcher!</b>\nAlerts are working correctly."
    )
    return {"sent": result}

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        upgrade_token=generate_upgrade_token(),
        referral_code=await generate_unique_referral_code(db),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)

@router.get("/me")
async def me(user: User = Depends(get_current_active_user)):
    max_sites = get_max_sites_for_user(user)
    return {
        "id": user.id,
        "email": user.email,
        "is_paid": user.is_paid,
        "telegram_chat_id": user.telegram_chat_id,
        "telegram_username": user.telegram_username,
        "upgrade_token": user.upgrade_token,
        "referral": {
            "code": user.referral_code,
            "referred_by_user_id": user.referred_by_user_id,
            "bonus_sites": user.referral_bonus_sites or 0,
        },
        "limits": {
            "max_sites": max_sites,
            "min_interval": settings.PAID_TIER_MIN_INTERVAL if user.is_paid else settings.FREE_TIER_MIN_INTERVAL,
        }
    }


@router.post("/me/apply-referral")
async def apply_referral(
    req: ApplyReferralRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    code = req.code.strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Referral code is required")

    if user.referred_by_user_id is not None:
        raise HTTPException(status_code=400, detail="Referral code already used")

    if user.referral_code and code == user.referral_code:
        raise HTTPException(status_code=400, detail="You cannot use your own referral code")

    inviter = await get_user_by_referral_code(db, code)
    if not inviter:
        raise HTTPException(status_code=404, detail="Referral code not found")
    if inviter.id == user.id:
        raise HTTPException(status_code=400, detail="You cannot use your own referral code")

    user.referred_by_user_id = inviter.id
    user.referral_bonus_sites = (user.referral_bonus_sites or 0) + 1
    inviter.referral_bonus_sites = (inviter.referral_bonus_sites or 0) + 1

    await db.commit()

    return {
        "ok": True,
        "message": "Referral applied: both users received +1 site limit",
        "limits": {
            "max_sites": get_max_sites_for_user(user),
            "min_interval": settings.PAID_TIER_MIN_INTERVAL if user.is_paid else settings.FREE_TIER_MIN_INTERVAL,
        },
    }

class TelegramRequest(BaseModel):
    chat_id: str

@router.patch("/me/telegram")
async def set_telegram(
    req: TelegramRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user.telegram_chat_id = req.chat_id
    await db.commit()
    return {"telegram_chat_id": user.telegram_chat_id}