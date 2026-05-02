from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Position:
    symbol: str
    side: str
    size: float
    entry_price: float
    current_price: float = 0.0
    leverage: int = 1
    hold_side: str = ""
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def pnl(self):
        if self.side == "long":
            return (self.current_price - self.entry_price) * self.size
        return (self.entry_price - self.current_price) * self.size

    @property
    def pnl_pct(self):
        if self.entry_price <= 0: return 0.0
        if self.side == "long":
            return (self.current_price - self.entry_price) / self.entry_price * 100
        return (self.entry_price - self.current_price) / self.entry_price * 100

    def update_price(self, price):
        self.current_price = price
        self.updated_at = datetime.now(timezone.utc)
