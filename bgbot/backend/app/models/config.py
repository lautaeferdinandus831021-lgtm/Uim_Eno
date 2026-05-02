from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, func
from app.core.database import Base


class ApiConfig(Base):
    __tablename__ = "api_configs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    api_key = Column(String(500), default="")
    api_secret = Column(String(500), default="")
    api_passphrase = Column(String(500), default="")
    demo = Column(Boolean, default=True)


class BotConfig(Base):
    __tablename__ = "bot_configs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    config_json = Column(JSON, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    config_json = Column(JSON, default=dict)
    metrics_json = Column(JSON, default=dict)
    trades_json = Column(JSON, default=list)
    equity_json = Column(JSON, default=list)
