from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, func, Text
from app.db.database import Base


class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    url = Column(String, nullable=False)
    name = Column(String, nullable=True)
    check_interval = Column(Integer, default=60)  # minutes
    is_active = Column(Boolean, default=True)

    # What to monitor
    monitor_availability = Column(Boolean, default=True)
    monitor_response_time = Column(Boolean, default=True)
    monitor_content_changes = Column(Boolean, default=False)
    response_time_threshold = Column(Float, default=5.0)  # seconds

    # Last known state
    last_status = Column(String, nullable=True)  # "up" | "down" | "unknown"
    last_response_time = Column(Float, nullable=True)
    last_content_hash = Column(String, nullable=True)
    last_content_snapshot = Column(Text, nullable=True)  # first 8000 characters of the page text
    last_checked_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    next_check_at = Column(DateTime, nullable=True)

    # Alert settings
    alert_on_down = Column(Boolean, default=True)
    alert_on_slow = Column(Boolean, default=True)
    alert_on_change = Column(Boolean, default=True)