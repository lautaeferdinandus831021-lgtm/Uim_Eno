from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from app.core.database import Base


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    trade_time = Column(DateTime(timezone=True), server_default=func.now())
    mode = Column(String(20), default="spot")
    side = Column(String(10), default="buy")
    pair = Column(String(20), default="")
    price = Column(Float, default=0)
    order_type = Column(String(20), default="market")
    size = Column(Float, default=0)
    pnl = Column(Float, default=0)
    pnl_pct = Column(Float, default=0)
    fee = Column(Float, default=0)
    status = Column(String(20), default="simulated")
    order_id = Column(String(100), default="")


class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(20), default="")
    side = Column(String(10), default="")
    size = Column(Float, default=0)
    entry_price = Column(Float, default=0)
    current_price = Column(Float, default=0)
    pnl = Column(Float, default=0)
    pnl_pct = Column(Float, default=0)
    hold_side = Column(String(10), default="")
    leverage = Column(Integer, default=1)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
