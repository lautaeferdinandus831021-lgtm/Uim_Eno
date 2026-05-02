from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime, timezone


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class Order:
    side: OrderSide
    symbol: str
    size: float
    price: Optional[float] = None
    order_type: OrderType = OrderType.MARKET
    tp_price: Optional[float] = None
    sl_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    order_id: str = ""
    fee: float = 0.0
    exchange: str = "bitget"
    mode: str = "spot"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_buy(self):
        return self.side == OrderSide.BUY

    def mark_filled(self, order_id, fee):
        self.status = OrderStatus.FILLED
        self.order_id = order_id
        self.fee = fee

    def mark_failed(self):
        self.status = OrderStatus.FAILED
