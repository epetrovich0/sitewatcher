from datetime import datetime, timedelta
from typing import Optional
import secrets
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.models.user import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(token: str, db: AsyncSession) -> Optional[User]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None
    return await get_user_by_id(db, user_id)


def generate_upgrade_token() -> str:
    return secrets.token_urlsafe(32)


async def get_user_by_referral_code(db: AsyncSession, referral_code: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.referral_code == referral_code))
    return result.scalar_one_or_none()


async def generate_unique_referral_code(db: AsyncSession) -> str:
    # Retry a few times to avoid very rare collisions.
    for _ in range(10):
        code = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()
        existing = await get_user_by_referral_code(db, code)
        if not existing:
            return code
    raise RuntimeError("Unable to generate unique referral code")


def get_max_sites_for_user(user: User) -> int:
    base_max_sites = settings.PAID_TIER_MAX_SITES if user.is_paid else settings.FREE_TIER_MAX_SITES
    bonus_sites = user.referral_bonus_sites or 0
    return base_max_sites + bonus_sites