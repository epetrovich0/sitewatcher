from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from app.db.database import get_db
from app.models.user import User
from app.services.auth import (
    hash_password, authenticate_user, create_access_token,
    get_user_by_email, get_current_user, generate_upgrade_token
)
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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
    return {
        "id": user.id,
        "email": user.email,
        "is_paid": user.is_paid,
        "telegram_chat_id": user.telegram_chat_id,
        "telegram_username": user.telegram_username,
        "limits": {
            "max_sites": settings.PAID_TIER_MAX_SITES if user.is_paid else settings.FREE_TIER_MAX_SITES,
            "min_interval": settings.PAID_TIER_MIN_INTERVAL if user.is_paid else settings.FREE_TIER_MIN_INTERVAL,
        }
    }
