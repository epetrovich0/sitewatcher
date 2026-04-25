from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from app.db.database import Base


class PaymentLog(Base):
    __tablename__ = "payment_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    amount = Column(Float, nullable=False)
    currency = Column(String, default="RUB")
    payment_method = Column(String, nullable=False)   # "telegram_stars", "stripe", "manual"
    status = Column(String, default="success")        # success, pending, failed
    external_id = Column(String, nullable=True)       # External payment ID
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())