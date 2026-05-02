import logging
from typing import Optional
from domain.trading.strategies import MACD451Strategy
from domain.trading.entities import Order
from shared.events import EventBus

logger = logging.getLogger("bgbot.trading_svc")


class TradingService:
    def __init__(self, cfg: dict, event_bus: Optional[EventBus] = None):
        self.cfg = cfg
        self.strategy = MACD451Strategy(cfg)
        self.event_bus = event_bus

    def analyze(self, df_m1, df_m5):
        m1_signal, m1_overlays = self.strategy.analyze_m1(df_m1)
        m5_signal, m5_overlays = self.strategy.analyze_m5(df_m5)
        p1 = float(df_m1["close"].iloc[-1])
        p5 = float(df_m5["close"].iloc[-1])
        aligned = m1_signal == m5_signal and m1_signal != "NEUTRAL"
        return {"m1": {"signal": m1_signal, "price": p1, "overlays": m1_overlays}, "m5": {"signal": m5_signal, "price": p5, "overlays": m5_overlays}, "aligned": aligned}

    def decide(self, m1_signal, m5_signal, prev_m5, balance, cooldown_active, user_id=0):
        should, signal = self.strategy.should_execute(m1_signal, m5_signal, prev_m5, balance, cooldown_active)
        if not should: return None
        size = self.strategy.calculate_size(0, balance)
        if size <= 0: return None
        side = "buy" if signal == "LONG" else "sell"
        return Order(side=side, symbol=self.cfg.get("symbol", "BTCUSDT"), size=size, mode=self.cfg.get("market_mode", "spot"))

    def record_result(self, pnl, user_id=0):
        self.strategy.risk.record_trade(pnl)

    @property
    def risk(self):
        return self.strategy.risk
