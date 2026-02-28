from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    telegram_chat_id = Column(String, nullable=True)
    telegram_username = Column(String, nullable=True)
    is_paid = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    # For Telegram-based upgrade flow
    upgrade_token = Column(String, nullable=True, unique=True)
