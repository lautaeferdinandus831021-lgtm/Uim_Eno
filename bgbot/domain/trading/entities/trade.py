from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone


@dataclass
class Trade:
    user_id: int
    mode: str
    side: str
    symbol: str
    entry_price: float
    exit_price: Optional[float] = None
    size: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    fee: float = 0.0
    status: str = "open"
    order_id: str = ""
    entry_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    exit_time: Optional[datetime] = None

    def close(self, exit_price, fee=0):
        self.exit_price = exit_price
        self.exit_time = datetime.now(timezone.utc)
        self.fee += fee
        if self.side == "buy":
            self.pnl = (exit_price - self.entry_price) * self.size - self.fee
        else:
            self.pnl = (self.entry_price - exit_price) * self.size - self.fee
        self.pnl_pct = (self.pnl / (self.entry_price * self.size)) * 100 if self.entry_price * self.size > 0 else 0
        self.status = "closed"

    @property
    def is_profitable(self):
        return self.pnl > 0
