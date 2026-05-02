import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger("bgbot.risk")


class RiskManager:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.daily_loss: float = 0.0
        self.last_day = datetime.now(timezone.utc).date()
        self.trade_timestamps: list = []

    def reset_daily(self):
        today = datetime.now(timezone.utc).date()
        if today != self.last_day:
            self.daily_loss = 0.0
            self.last_day = today

    def check_daily_loss(self, balance):
        self.reset_daily()
        max_pct = self.cfg.get("max_daily_loss_pct", 5.0)
        if balance <= 0:
            return False
        loss_pct = (self.daily_loss / balance) * 100
        if loss_pct >= max_pct:
            logger.warning(f"Risk BLOCKED: daily loss {loss_pct:.1f}% >= {max_pct}%")
            return False
        return True

    def check_trade_limit(self):
        now = time.time()
        self.trade_timestamps = [t for t in self.trade_timestamps if now - t < 3600]
        max_per_hour = self.cfg.get("max_trades_per_hour", 10)
        if len(self.trade_timestamps) >= max_per_hour:
            logger.warning(f"Risk BLOCKED: trade limit {len(self.trade_timestamps)} >= {max_per_hour}/hr")
            return False
        return True

    def check_position_size(self, size, balance):
        max_pct = self.cfg.get("risk_pct", 1.0)
        max_size = balance * (max_pct / 100)
        if size > max_size:
            logger.warning(f"Risk: size ${size:.2f} > max ${max_size:.2f}")
            return max_size
        return size

    def record_trade(self, pnl):
        self.trade_timestamps.append(time.time())
        if pnl < 0:
            self.daily_loss += abs(pnl)

    def get_status(self, balance):
        self.reset_daily()
        now = time.time()
        active = len([t for t in self.trade_timestamps if now - t < 3600])
        return {"daily_loss": round(self.daily_loss, 2), "daily_loss_pct": round((self.daily_loss / balance * 100) if balance > 0 else 0, 2), "trades_this_hour": active, "max_trades_per_hour": self.cfg.get("max_trades_per_hour", 10), "can_trade": self.check_daily_loss(balance) and self.check_trade_limit()}
