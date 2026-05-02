import logging
from typing import Tuple
from domain.trading.indicators import MACD
from domain.trading.risk import RiskManager

logger = logging.getLogger("bgbot.strategy")


class MACD451Strategy:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.macd = MACD(fast=cfg.get("macd_fast", 4), slow=cfg.get("macd_slow", 5), signal=cfg.get("macd_signal", 1))
        self.risk = RiskManager(cfg)

    def analyze_m1(self, df):
        return self.macd.compute(df, overlays=True)

    def analyze_m5(self, df):
        return self.macd.compute(df, overlays=True)

    def should_execute(self, m1_signal, m5_signal, prev_m5, balance, cooldown_active) -> Tuple[bool, str]:
        aligned = m1_signal == m5_signal and m1_signal != "NEUTRAL"
        if not aligned: return False, "NEUTRAL"
        if m5_signal == prev_m5: return False, m5_signal
        if cooldown_active: return False, m5_signal
        if not self.risk.check_daily_loss(balance): return False, "BLOCKED_DAILY"
        if not self.risk.check_trade_limit(): return False, "BLOCKED_LIMIT"
        return True, m5_signal

    def calculate_size(self, price, balance):
        cfg = self.cfg
        if cfg.get("use_balance_pct") and balance > 0:
            size = balance * (cfg.get("risk_pct", 1.0) / 100)
        else:
            size = cfg.get("order_size", 50)
        return self.risk.check_position_size(size, balance)

    def calculate_tp_sl(self, entry_price, signal):
        tp_pct = self.cfg.get("tp_percent", 2.5) / 100
        sl_pct = self.cfg.get("sl_percent", 1.5) / 100
        if signal == "LONG":
            tp = round(entry_price * (1 + tp_pct), 2)
            sl = round(entry_price * (1 - sl_pct), 2)
        else:
            tp = round(entry_price * (1 - tp_pct), 2)
            sl = round(entry_price * (1 + sl_pct), 2)
        return tp, sl
