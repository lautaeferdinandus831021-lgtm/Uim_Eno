from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from app.core.database import Base


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(64), nullable=False)
    device_name = Column(String(100), default="")
    user_agent = Column(String(500), default="")
    approved = Column(Boolean, default=True)
    created_at = Column(Float, default=0)
    last_seen = Column(Float, default=0)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(64), default="")
    ip = Column(String(50), default="")
    user_agent = Column(String(500), default="")
    created_at = Column(Float, default=0)
    last_used = Column(Float, default=0)
    expires_at = Column(Float, default=0)
    revoked = Column(Boolean, default=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(64), default="")
    created_at = Column(Float, default=0)
    expires_at = Column(Float, default=0)
    revoked = Column(Boolean, default=False)


class SecurityLog(Base):
    __tablename__ = "security_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    event = Column(String(100), nullable=False)
    ip = Column(String(50), default="")
    device_id = Column(String(64), default="")
    user_agent = Column(String(500), default="")
    geo_json = Column(String(500), default="{}")
    details = Column(String(500), default="")
    created_at = Column(Float, default=0)
