import numpy as np
import pandas as pd
from typing import Dict, List
from domain.trading.indicators import MACD
from domain.backtest.metrics import BacktestMetrics


class BacktestEngine:
    def __init__(self, cfg: dict):
        self.macd = MACD(fast=cfg.get("macd_fast", 4), slow=cfg.get("macd_slow", 5), signal=cfg.get("macd_signal", 1))
        self.tp_pct = cfg.get("tp_percent", 2.5) / 100
        self.sl_pct = cfg.get("sl_percent", 1.5) / 100
        self.order_size = cfg.get("order_size", 50)
        self.fee_pct = 0.001
        self.slip = 0.0008
        self.spread = 0.0003

    def run(self, df, initial_balance=10000):
        lookback = 20
        if len(df) < lookback + 10:
            return {"error": "Not enough data. Need 30+ candles."}
        balance = initial_balance
        position = None
        trades: List[Dict] = []
        equity: List[Dict] = []
        peak = initial_balance
        max_dd = 0.0
        max_dd_pct = 0.0
        prev_signal = "NEUTRAL"
        for i in range(lookback, len(df)):
            window = df.iloc[i - lookback:i + 1]
            price = float(df.iloc[i]["close"])
            high = float(df.iloc[i]["high"])
            low = float(df.iloc[i]["low"])
            ts = int(df.iloc[i]["timestamp"].timestamp())
            if position:
                hit, ep = self._check_exit(position, high, low)
                if hit:
                    pnl = self._calc_pnl(position, ep)
                    fee = ep * position["size"] * self.fee_pct
                    pnl -= fee
                    balance += pnl
                    trades.append({"entry_time": position["time"], "exit_time": ts, "side": position["side"], "entry": position["entry"], "exit": round(ep, 2), "size": position["size"], "pnl": round(pnl, 2), "pnl_pct": round(pnl / (position["entry"] * position["size"]) * 100, 2), "fee": round(fee, 2), "exit_type": "TP_SL"})
                    position = None
            signal = self.macd.compute_fast(window)
            if position is None and signal != "NEUTRAL" and signal != prev_signal:
                ep = self._entry_price(price, signal)
                sz = self.order_size / ep
                fee = ep * sz * self.fee_pct
                balance -= fee
                tp, sl = self._calc_tp_sl(ep, signal)
                position = {"side": signal, "entry": ep, "size": sz, "tp": tp, "sl": sl, "time": ts}
            prev_signal = signal
            unr = 0.0
            if position:
                unr = ((price - position["entry"]) if position["side"] == "LONG" else (position["entry"] - price)) * position["size"]
            eq = balance + unr
            equity.append({"time": ts, "value": round(eq, 2)})
            peak = max(peak, eq)
            dd = peak - eq
            max_dd = max(max_dd, dd)
            max_dd_pct = max(max_dd_pct, (dd / peak * 100) if peak > 0 else 0)
        if position:
            lp = float(df.iloc[-1]["close"])
            ep = self._exit_price(lp, position["side"])
            pnl = self._calc_pnl(position, ep)
            fee = ep * position["size"] * self.fee_pct
            pnl -= fee
            balance += pnl
            trades.append({"entry_time": position["time"], "exit_time": int(df.iloc[-1]["timestamp"].timestamp()), "side": position["side"], "entry": position["entry"], "exit": round(ep, 2), "size": position["size"], "pnl": round(pnl, 2), "pnl_pct": round(pnl / (position["entry"] * position["size"]) * 100, 2), "fee": round(fee, 2), "exit_type": "END"})
        metrics = BacktestMetrics.calculate(initial_balance, balance, trades, max_dd, max_dd_pct)
        return {"metrics": metrics, "trades": trades, "equity": equity}

    def _entry_price(self, p, s):
        c = p * (self.slip + self.spread)
        return p + c if s == "LONG" else p - c

    def _exit_price(self, p, s):
        c = p * (self.slip + self.spread)
        return p - c if s == "LONG" else p + c

    def _check_exit(self, pos, high, low):
        if pos["side"] == "LONG":
            if high >= pos["tp"]: return True, self._exit_price(pos["tp"], "LONG")
            if low <= pos["sl"]: return True, self._exit_price(pos["sl"], "LONG")
        else:
            if low <= pos["tp"]: return True, self._exit_price(pos["tp"], "SHORT")
            if high >= pos["sl"]: return True, self._exit_price(pos["sl"], "SHORT")
        return False, 0

    def _calc_pnl(self, pos, exit_price):
        if pos["side"] == "LONG":
            return (exit_price - pos["entry"]) * pos["size"]
        return (pos["entry"] - exit_price) * pos["size"]

    def _calc_tp_sl(self, entry, signal):
        if signal == "LONG":
            return round(entry * (1 + self.tp_pct), 2), round(entry * (1 - self.sl_pct), 2)
        return round(entry * (1 - self.tp_pct), 2), round(entry * (1 + self.sl_pct), 2)
