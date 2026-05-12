import asyncio
import json
import logging
import time
from datetime import datetime
from collections import deque

import pandas as pd
import pandas_ta as ta

logger = logging.getLogger("bgbot.ws")


class MACDEngine:
    """MACD + RSI engine. Aggregates ticks into candles, computes indicators from completed candle closes."""

    def __init__(self, fast=4, slow=5, signal=3, label="M1", source="close", ticks_per_candle=60):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.label = label
        self.source = source

        # === Candle Aggregation (60=M1, 300=M5) ===
        self.ticks_per_candle = ticks_per_candle
        self._candle_tick = 0
        self._candle_open = 0.0
        self._candle_high = 0.0
        self._candle_low = float("inf")
        self._candle_close = 0.0

        # === Completed candle closes ===
        self.candle_closes = deque(maxlen=200)

        # === MACD state ===
        self.macd_val = 0.0
        self.signal_val = 0.0
        self.hist_val = 0.0
        self.macd_hist = deque(maxlen=60)
        self.signal_hist = deque(maxlen=60)
        self.hist_hist = deque(maxlen=60)

        # === RSI state ===
        self.rsi_val = 50.0
        self.rsi_period = 6

        # === Signal ===
        self.buy_sell = "-"
        self.signal_name = "-"
        self.last_update = 0
        self.tick_count = 0

        # === All tick prices (for peak/trough display) ===
        self.prices = deque(maxlen=200)

    def update(self, price, open_p=None, high=None, low=None):
        """Receive tick price. Accumulate into candle. On candle close: compute MACD + RSI."""
        if self.source == "close" or open_p is None:
            calc_price = price
        elif self.source == "open" and open_p is not None:
            calc_price = open_p
        elif self.source == "high" and high is not None:
            calc_price = high
        elif self.source == "low" and low is not None:
            calc_price = low
        elif self.source == "hl2" and high is not None and low is not None:
            calc_price = (high + low) / 2
        elif self.source == "hlc3" and high is not None and low is not None:
            calc_price = (high + low + price) / 3
        elif self.source == "hlcc4" and high is not None and low is not None:
            calc_price = (high + low + price + price) / 4
        else:
            calc_price = price

        self.prices.append(calc_price)
        self.tick_count += 1
        self.last_update = time.time()

        # === Accumulate into forming candle ===
        self._candle_tick += 1
        if self._candle_tick == 1:
            self._candle_open = calc_price
            self._candle_high = calc_price
            self._candle_low = calc_price
        else:
            if calc_price > self._candle_high:
                self._candle_high = calc_price
            if calc_price < self._candle_low:
                self._candle_low = calc_price
        self._candle_close = calc_price

        # === Candle completed: finalize and recalculate ===
        if self._candle_tick >= self.ticks_per_candle:
            self.candle_closes.append(self._candle_close)
            logger.debug(
                "%s candle #%d done: O=%.2f H=%.2f L=%.2f C=%.2f",
                self.label, len(self.candle_closes),
                self._candle_open, self._candle_high, self._candle_low, self._candle_close,
            )
            self._candle_tick = 0
            self._candle_open = 0.0
            self._candle_high = 0.0
            self._candle_low = float("inf")
            self._candle_close = 0.0
            self._recalc_latest()

    def seed_candle(self, close_price):
        """Add historical candle close directly (for kline seeding, bypasses tick aggregation)."""
        self.candle_closes.append(close_price)
        self.prices.append(close_price)

    def seed_init(self):
        """After ALL candles are seeded, compute full MACD+RSI history from all candle closes."""
        closes = list(self.candle_closes)
        if len(closes) < 10:
            return
        series = pd.Series(closes)

        # --- MACD: compute all values, fill full history ---
        try:
            r = ta.macd(series, fast=self.fast, slow=self.slow, signal=self.signal)
            if r is not None and not r.empty:
                cols = r.columns.tolist()
                mc = [c for c in cols if c.startswith("MACD_") and "h_" not in c and "s_" not in c]
                hc = [c for c in cols if c.startswith("MACDh_")]
                sc = [c for c in cols if c.startswith("MACDs_")]
                for i in range(len(r)):
                    if mc and pd.notna(r.iloc[i][mc[0]]):
                        self.macd_hist.append(float(r.iloc[i][mc[0]]))
                    if sc and pd.notna(r.iloc[i][sc[0]]):
                        self.signal_hist.append(float(r.iloc[i][sc[0]]))
                    if hc and pd.notna(r.iloc[i][hc[0]]):
                        self.hist_hist.append(float(r.iloc[i][hc[0]]))
                last = r.iloc[-1]
                if mc:
                    self.macd_val = float(last[mc[0]]) if pd.notna(last[mc[0]]) else 0
                if sc:
                    self.signal_val = float(last[sc[0]]) if pd.notna(last[sc[0]]) else 0
                if hc:
                    self.hist_val = float(last[hc[0]]) if pd.notna(last[hc[0]]) else 0
                if self.macd_val > self.signal_val:
                    self.buy_sell = "BUY"
                    self.signal_name = "LONG"
                elif self.macd_val < self.signal_val:
                    self.buy_sell = "SELL"
                    self.signal_name = "SHORT"
                else:
                    self.buy_sell = "HOLD"
                    self.signal_name = "NEUTRAL"
        except Exception as e:
            logger.error("MACD seed %s: %s", self.label, e)

        # --- RSI: compute from all seeded candles ---
        try:
            rsi = ta.rsi(series, length=self.rsi_period)
            if rsi is not None and len(rsi) > 0:
                last_rsi = rsi.iloc[-1]
                if pd.notna(last_rsi):
                    self.rsi_val = float(last_rsi)
        except Exception as e:
            logger.error("RSI seed %s: %s", self.label, e)

        logger.info(
            "%s seed_init: %d candles, %d MACD history, RSI=%.2f",
            self.label, len(closes), len(self.macd_hist), self.rsi_val,
        )

    def _recalc_latest(self):
        """Recalculate MACD + RSI from completed candle closes (incremental, append to history)."""
        closes = list(self.candle_closes)
        if len(closes) < 10:
            return
        series = pd.Series(closes)

        # --- MACD ---
        try:
            r = ta.macd(series, fast=self.fast, slow=self.slow, signal=self.signal)
            if r is not None and not r.empty:
                last = r.iloc[-1]
                cols = r.columns.tolist()
                mc = [c for c in cols if c.startswith("MACD_") and "h_" not in c and "s_" not in c]
                hc = [c for c in cols if c.startswith("MACDh_")]
                sc = [c for c in cols if c.startswith("MACDs_")]
                if mc:
                    self.macd_val = float(last[mc[0]]) if pd.notna(last[mc[0]]) else 0
                if sc:
                    self.signal_val = float(last[sc[0]]) if pd.notna(last[sc[0]]) else 0
                if hc:
                    self.hist_val = float(last[hc[0]]) if pd.notna(last[hc[0]]) else 0
                self.macd_hist.append(self.macd_val)
                self.signal_hist.append(self.signal_val)
                self.hist_hist.append(self.hist_val)
                if self.macd_val > self.signal_val:
                    self.buy_sell = "BUY"
                    self.signal_name = "LONG"
                elif self.macd_val < self.signal_val:
                    self.buy_sell = "SELL"
                    self.signal_name = "SHORT"
                else:
                    self.buy_sell = "HOLD"
                    self.signal_name = "NEUTRAL"
        except Exception as e:
            logger.error("MACD %s: %s", self.label, e)

        # --- RSI ---
        try:
            rsi = ta.rsi(series, length=self.rsi_period)
            if rsi is not None and len(rsi) > 0:
                val = rsi.iloc[-1]
                if pd.notna(val):
                    self.rsi_val = float(val)
        except Exception as e:
            logger.error("RSI %s: %s", self.label, e)

    def get_state(self):
        return {
            "macd": round(self.macd_val, 8),
            "signal_line": round(self.signal_val, 8),
            "histogram": round(self.hist_val, 8),
            "signal": self.signal_name,
            "buy_sell": self.buy_sell,
            "macd_history": list(self.macd_hist),
            "signal_history": list(self.signal_hist),
            "hist_history": list(self.hist_hist),
            "close_history": list(self.candle_closes)[-60:],
            "ema_fast": 0,
            "ema_slow": 0,
            "candles": len(self.candle_closes),
            "rsi": round(self.rsi_val, 2),
            "rsi_zone": (
                "oversold" if self.rsi_val <= 28
                else "weak" if self.rsi_val <= 42
                else "neutral" if self.rsi_val <= 56
                else "strong" if self.rsi_val <= 70
                else "overbought" if self.rsi_val <= 84
                else "extreme_overbought"
            ),
            "momentum": "Bullish" if self.hist_val > 0 else "Bearish" if self.hist_val < 0 else "Flat",
            "volatility": round(abs(self.hist_val), 8),
            "macd_pct_from_zero": round(self.macd_val * 10000, 2),
            "hist_pct_from_zero": round(self.hist_val * 10000, 2),
            "peak_close": max(self.prices) if self.prices else 0,
            "trough_close": min(self.prices) if self.prices else 0,
            "last_update": self.last_update,
            "tick_count": self.tick_count,
            "ticks_per_candle": self.ticks_per_candle,
            "completed_candles": len(self.candle_closes),
            "current_candle_ticks": self._candle_tick,
        }

    def reset(self, keep_candles=False):
        """Reset engine state. keep_candles=True preserves candle data for param changes."""
        if not keep_candles:
            self.candle_closes.clear()
            self.prices.clear()
        self.macd_hist.clear()
        self.signal_hist.clear()
        self.hist_hist.clear()
        self.macd_val = self.signal_val = self.hist_val = 0
        self.rsi_val = 50.0
        self._candle_tick = 0
        self._candle_open = 0.0
        self._candle_high = 0.0
        self._candle_low = float("inf")
        self._candle_close = 0.0
        self.buy_sell = self.signal_name = "-"
        self.tick_count = 0


class BitgetWebSocket:
    def __init__(self, m1_fast=4, m1_slow=5, m1_sig=3, m5_fast=4, m5_slow=5, m5_sig=3, pair="BTCUSDT"):
        self.m1 = MACDEngine(fast=m1_fast, slow=m1_slow, signal=m1_sig, label="M1", ticks_per_candle=60)
        self.m5 = MACDEngine(fast=m5_fast, slow=m5_slow, signal=m5_sig, label="M5", ticks_per_candle=300)
        self.price = 0.0
        self.connected = False
        self.last_tick = 0
        self._running = False
        self.pair = pair
        self.bb_data = {
            "bb_upper": 0, "bb_mid": 0, "bb_lower": 0,
            "bb_pct_from_support": 0, "bb_pct_from_peak": 0,
            "bb_bandwidth": 0, "bb_length": 20, "bb_std": 2.0,
        }
        self.ticker_data = {"high24h": 0, "low24h": 0, "volume24h": 0, "change24h": 0}
        self._config_store = None
        self._bb_closes = []

    async def start(self):
        self._running = True
        await self._seed("1min", self.m1)
        await self._seed("5min", self.m5)
        await self._seed_bb_closes()
        if self._config_store:
            self.m1.rsi_period = int(self._config_store.get("m1_rsi_length", 6))
            self.m5.rsi_period = int(self._config_store.get("m5_rsi_length", 6))
        asyncio.create_task(self._realtime_loop())
        logger.info(
            "BitgetWebSocket started: M1(%d tick/candle, %d seeded, %d macd_hist) M5(%d tick/candle, %d seeded, %d macd_hist)",
            self.m1.ticks_per_candle, len(self.m1.candle_closes), len(self.m1.macd_hist),
            self.m5.ticks_per_candle, len(self.m5.candle_closes), len(self.m5.macd_hist),
        )

    async def stop(self):
        self._running = False

    async def _seed_bb_closes(self):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10, verify=False) as c:
                r = await c.get(
                    "https://api.bitget.com/api/v2/spot/market/candles",
                    params={"symbol": self.pair, "granularity": "1min", "limit": "100"},
                )
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    if data:
                        self._bb_closes = [float(row[4]) for row in reversed(data)]
                        logger.info("BB seeded %d closes from 1min candles", len(self._bb_closes))
        except Exception as e:
            logger.error("BB seed: %s", e)

    async def _realtime_loop(self):
        import httpx
        logger.info("Real-time loop started (1s interval, tick->candle->MACD+RSI)")
        tick = 0
        bb_len = 6
        bb_std_val = 1.2
        if self._config_store:
            bb_len = int(self._config_store.get("m1_bb_length", 6))
            bb_std_val = float(self._config_store.get("m1_bb_std", 1.2))
        self.bb_data["bb_length"] = bb_len
        self.bb_data["bb_std"] = bb_std_val

        while self._running:
            try:
                async with httpx.AsyncClient(timeout=5, verify=False) as c:
                    r = await c.get(
                        "https://api.bitget.com/api/v2/spot/market/tickers",
                        params={"symbol": self.pair},
                    )
                    if r.status_code == 200:
                        data = r.json().get("data", [])
                        if data:
                            t = data[0]
                            p = float(t.get("lastPr", 0))
                            if p > 0:
                                self.price = p
                                self.last_tick = time.time()
                                self.connected = True
                                self.m1.update(p)
                                self.m5.update(p)
                                self.ticker_data = {
                                    "high24h": float(t.get("high24h", 0)),
                                    "low24h": float(t.get("low24h", 0)),
                                    "volume24h": float(t.get("usdtVolume", 0) or t.get("baseVolume", 0)),
                                    "change24h": float(t.get("change24h", 0)),
                                }
                                bb_needs_update = (self.bb_data["bb_mid"] == 0) or (tick % 30 == 0 and tick > 5)
                                if bb_needs_update:
                                    try:
                                        async with httpx.AsyncClient(timeout=8, verify=False) as c2:
                                            cr = await c2.get(
                                                "https://api.bitget.com/api/v2/spot/market/candles",
                                                params={"symbol": self.pair, "granularity": "1min", "limit": "50"},
                                            )
                                            if cr.status_code == 200:
                                                cdata = cr.json().get("data", [])
                                                if cdata and len(cdata) >= bb_len:
                                                    self._bb_closes = [float(row[4]) for row in reversed(cdata)]
                                    except Exception as e:
                                        logger.error("BB candle refresh: %s", e)
                                if len(self._bb_closes) >= bb_len:
                                    try:
                                        import pandas as _pd
                                        import pandas_ta as _pd_ta
                                        series = _pd.Series(self._bb_closes[-50:])
                                        bb = _pd_ta.bbands(series, length=bb_len, std=bb_std_val)
                                        if bb is not None and len(bb) > 0:
                                            cols = bb.columns.tolist()
                                            bb_lower = float(bb[cols[0]].iloc[-1])
                                            bb_mid = float(bb[cols[1]].iloc[-1])
                                            bb_upper = float(bb[cols[2]].iloc[-1])
                                            bb_range = bb_upper - bb_lower
                                            pct_up = round(((p - bb_lower) / bb_range) * 100, 2) if bb_range > 0 else 0
                                            pct_down = round(((bb_upper - p) / bb_range) * 100, 2) if bb_range > 0 else 0
                                            bw = round((bb_range / bb_mid) * 100, 2) if bb_mid > 0 else 0
                                            self.bb_data = {
                                                "bb_upper": bb_upper, "bb_mid": bb_mid, "bb_lower": bb_lower,
                                                "bb_pct_from_support": pct_up, "bb_pct_from_peak": pct_down,
                                                "bb_bandwidth": bw, "bb_length": bb_len, "bb_std": bb_std_val,
                                            }
                                    except Exception as e:
                                        logger.error("BB calc: %s", e)
                                tick += 1
                                if tick % 30 == 0 and self._config_store:
                                    bb_len = int(self._config_store.get("m1_bb_length", 6))
                                    bb_std_val = float(self._config_store.get("m1_bb_std", 1.2))
                                    self.bb_data["bb_length"] = bb_len
                                    self.bb_data["bb_std"] = bb_std_val
            except Exception as e:
                logger.error("Real-time loop: %s", e)
                self.connected = False
            await asyncio.sleep(1)

    async def _seed(self, tf, engine):
        """Seed historical klines as completed candles, then compute full MACD+RSI history."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10, verify=False) as c:
                r = await c.get(
                    "https://api.bitget.com/api/v2/spot/market/candles",
                    params={"symbol": self.pair, "granularity": tf, "limit": "200"},
                )
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    for row in reversed(data):
                        if len(row) >= 5:
                            engine.seed_candle(float(row[4]))
                    engine.seed_init()
                    logger.info(
                        "Seeded %d candles for %s -> %d macd_hist, RSI=%.2f",
                        len(data), engine.label, len(engine.macd_hist), engine.rsi_val,
                    )
        except Exception as e:
            logger.error("Seed %s: %s", tf, e)

    def get_analysis(self):
        m1 = self.m1.get_state()
        m5 = self.m5.get_state()
        m1a = m1["macd"] > 0
        m5a = m5["macd"] > 0
        aligned = (m1a and m5a) or (not m1a and not m5a)
        sig = "LONG" if m1a and m5a else "SHORT" if not m1a and not m5a else "NEUTRAL"
        return {
            "m1": m1, "m5": m5, "aligned": aligned, "trade_signal": sig,
            "timestamp": datetime.now().strftime("%H:%M:%S"), "price": self.price,
            "connected": self.connected, "last_tick": self.last_tick,
            "bb": self.bb_data, "ticker": self.ticker_data,
        }

    def update_params(self, m1_fast, m1_slow, m1_sig, m5_fast, m5_slow, m5_sig, m1_source=None, m5_source=None):
        self.m1.fast = m1_fast
        self.m1.slow = m1_slow
        self.m1.signal = m1_sig
        self.m5.fast = m5_fast
        self.m5.slow = m5_slow
        self.m5.signal = m5_sig
        if m1_source:
            self.m1.source = m1_source
        if m5_source:
            self.m5.source = m5_source
        if self._config_store:
            self.m1.rsi_period = int(self._config_store.get("m1_rsi_length", 6))
            self.m5.rsi_period = int(self._config_store.get("m5_rsi_length", 6))
        self.m1.reset(keep_candles=True)
        self.m5.reset(keep_candles=True)
        self.m1.seed_init()
        self.m5.seed_init()
        logger.info(
            "MACD params: M1(%d-%d-%d) M5(%d-%d-%d), history recalc done: M1=%d M5=%d",
            m1_fast, m1_slow, m1_sig, m5_fast, m5_slow, m5_sig,
            len(self.m1.macd_hist), len(self.m5.macd_hist),
        )

    async def update_pair(self, new_pair):
        if new_pair != self.pair:
            self.pair = new_pair
            self.price = 0.0
            self.connected = False
            self.m1.reset()
            self.m5.reset()
            await self._seed("1min", self.m1)
            await self._seed("5min", self.m5)
            logger.info("Pair changed to %s, re-seeded M1+M5", new_pair)
