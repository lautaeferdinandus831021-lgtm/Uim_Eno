from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), default="")
    picture = Column(String(512), default="")
    provider = Column(String(50), default="email")
    password_hash = Column(String(255), default="")
    totp_secret = Column(String(255), default="")
    totp_enabled = Column(Boolean, default=False)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(Float, default=0)
    reset_token = Column(String(255), default="")
    reset_token_expires = Column(Float, default=0)
    last_login = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
