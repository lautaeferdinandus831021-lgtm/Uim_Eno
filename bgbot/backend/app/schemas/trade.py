from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TradeResponse(BaseModel):
    id: int
    trade_time: Optional[datetime] = None
    mode: str
    side: str
    pair: str
    price: float
    pnl: float
    status: str

    class Config:
        from_attributes = True
