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
    def __init__(self, fast=4, slow=5, signal=3, label="M1", source="close"):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.label = label
        self.source = source
        self.prices = deque(maxlen=200)
        self.macd_val = 0.0
        self.signal_val = 0.0
        self.hist_val = 0.0
        self.macd_hist = deque(maxlen=60)
        self.signal_hist = deque(maxlen=60)
        self.hist_hist = deque(maxlen=60)
        self.buy_sell = "-"
        self.signal_name = "-"
        self.last_update = 0
        self.tick_count = 0

    def update(self, price, open_p=None, high=None, low=None):
        """Update with OHLC data. price = close by default"""
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
        if len(self.prices) < 10:
            return
        try:
            df = pd.DataFrame({"Close": list(self.prices)})
            r = ta.macd(df["Close"], fast=self.fast, slow=self.slow, signal=self.signal)
            if r is not None and not r.empty:
                last = r.iloc[-1]
                cols = r.columns.tolist()
                mc = [c for c in cols if c.startswith("MACD_") and "h_" not in c and "s_" not in c]
                hc = [c for c in cols if c.startswith("MACDh_")]
                sc = [c for c in cols if c.startswith("MACDs_")]
                if mc: self.macd_val = float(last[mc[0]]) if pd.notna(last[mc[0]]) else 0
                if sc: self.signal_val = float(last[sc[0]]) if pd.notna(last[sc[0]]) else 0
                if hc: self.hist_val = float(last[hc[0]]) if pd.notna(last[hc[0]]) else 0
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
            logger.error(f"MACD {self.label}: {e}")

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
            "close_history": list(self.prices)[-60:],
            "ema_fast": 0, "ema_slow": 0,
            "candles": len(self.prices),
            "momentum": "Bullish" if self.hist_val > 0 else "Bearish" if self.hist_val < 0 else "Flat",
            "volatility": round(abs(self.hist_val), 8),
            "macd_pct_from_zero": round(self.macd_val * 10000, 2),
            "hist_pct_from_zero": round(self.hist_val * 10000, 2),
            "peak_close": max(self.prices) if self.prices else 0,
            "trough_close": min(self.prices) if self.prices else 0,
            "last_update": self.last_update,
            "tick_count": self.tick_count,
        }

    def reset(self):
        self.prices.clear()
        self.macd_hist.clear()
        self.signal_hist.clear()
        self.hist_hist.clear()
        self.macd_val = self.signal_val = self.hist_val = 0
        # Keep source setting
        self.buy_sell = self.signal_name = "-"
        self.tick_count = 0


class BitgetWebSocket:
    def __init__(self, m1_fast=4, m1_slow=5, m1_sig=3, m5_fast=4, m5_slow=5, m5_sig=3, pair="BTCUSDT"):
        self.m1 = MACDEngine(fast=m1_fast, slow=m1_slow, signal=m1_sig, label="M1")
        self.m5 = MACDEngine(fast=m5_fast, slow=m5_slow, signal=m5_sig, label="M5")
        self.price = 0.0
        self.connected = False
        self.last_tick = 0
        self._running = False
        self.pair = pair
        # BB state (updated every tick)
        self.bb_data = {"bb_upper": 0, "bb_mid": 0, "bb_lower": 0, "bb_pct_from_support": 0, "bb_pct_from_peak": 0, "bb_bandwidth": 0, "bb_length": 20, "bb_std": 2.0}
        # Ticker 24h state
        self.ticker_data = {"high24h": 0, "low24h": 0, "volume24h": 0, "change24h": 0}
        # Config store reference (set externally)
        self._config_store = None
        self._bb_closes = []  # rolling closes for BB
        self._bb_tick_count = 0

    async def start(self):
        self._running = True
        # Seed historical klines first
        await self._seed("1min", self.m1)
        await self._seed("5min", self.m5)
        # Seed BB closes from candle history
        await self._seed_bb_closes()
        # Start real-time loop
        asyncio.create_task(self._realtime_loop())
        logger.info("BitgetWebSocket started: M1+M5+BB seeded, real-time loop active")

    async def stop(self):
        self._running = False

    async def _seed_bb_closes(self):
        """Seed rolling closes for BB calculation from candle history"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10, verify=False) as c:
                r = await c.get("https://api.bitget.com/api/v2/spot/market/candles",
                                params={"symbol": self.pair, "granularity": "1min", "limit": "100"})
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    if data:
                        # data[0] = newest candle, reverse for oldest-first
                        self._bb_closes = [float(row[4]) for row in reversed(data)]
                        logger.info(f"BB seeded {len(self._bb_closes)} closes from 1min candles")
        except Exception as e:
            logger.error(f"BB seed: {e}")

    async def _realtime_loop(self):
        """Single loop: fetch price every 1s, feed MACD + update BB + ticker"""
        import httpx
        logger.info("Real-time loop started (1s interval, MACD+BB+ticker)")
        tick = 0
        # BB warmup: seed closes from config
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
                    # Fetch price + ticker
                    r = await c.get("https://api.bitget.com/api/v2/spot/market/tickers",
                                    params={"symbol": self.pair})
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

                                # Update ticker
                                self.ticker_data = {
                                    "high24h": float(t.get("high24h", 0)),
                                    "low24h": float(t.get("low24h", 0)),
                                    "volume24h": float(t.get("usdtVolume", 0) or t.get("baseVolume", 0)),
                                    "change24h": float(t.get("change24h", 0))
                                }

                                # BB: recalculate from candle closes + current live price as "in-progress"
                                # Only recalc from candles every 30 ticks OR if bb not yet set
                                bb_needs_update = (self.bb_data["bb_mid"] == 0) or (tick % 30 == 0 and tick > 5)
                                if bb_needs_update:
                                    try:
                                        # Refresh candle data for accurate BB
                                        async with httpx.AsyncClient(timeout=8, verify=False) as c2:
                                            cr = await c2.get("https://api.bitget.com/api/v2/spot/market/candles",
                                                              params={"symbol": self.pair, "granularity": "1min", "limit": "50"})
                                            if cr.status_code == 200:
                                                cdata = cr.json().get("data", [])
                                                if cdata and len(cdata) >= bb_len:
                                                    self._bb_closes = [float(row[4]) for row in reversed(cdata)]
                                    except Exception as e:
                                        logger.error(f"BB candle refresh: {e}")

                                # Always recalc BB% from current price (using cached BB bands)
                                if len(self._bb_closes) >= bb_len:
                                    try:
                                        import pandas as pd
                                        import pandas_ta as _pd_ta
                                        series = pd.Series(self._bb_closes[-50:])
                                        bb = _pd_ta.bbands(series, length=bb_len, std=bb_std_val)
                                        if bb is not None and len(bb) > 0:
                                            cols = bb.columns.tolist()
                                            bb_lower = float(bb[cols[0]].iloc[-1])
                                            bb_mid = float(bb[cols[1]].iloc[-1])
                                            bb_upper = float(bb[cols[2]].iloc[-1])
                                            bb_range = bb_upper - bb_lower
                                            # Use LIVE price for position calculation
                                            pct_up = round(((p - bb_lower) / bb_range) * 100, 2) if bb_range > 0 else 0
                                            pct_down = round(((bb_upper - p) / bb_range) * 100, 2) if bb_range > 0 else 0
                                            bw = round((bb_range / bb_mid) * 100, 2) if bb_mid > 0 else 0
                                            self.bb_data = {
                                                "bb_upper": bb_upper, "bb_mid": bb_mid, "bb_lower": bb_lower,
                                                "bb_pct_from_support": pct_up, "bb_pct_from_peak": pct_down,
                                                "bb_bandwidth": bw, "bb_length": bb_len, "bb_std": bb_std_val
                                            }
                                    except Exception as e:
                                        logger.error(f"BB calc: {e}")

                                if tick % 30 == 0 and tick > 10:
                                    pass  # candle refresh done above

                                tick += 1
                                # Re-read config every 30 ticks
                                if tick % 30 == 0 and self._config_store:
                                    bb_len = int(self._config_store.get("m1_bb_length", 6))
                                    bb_std_val = float(self._config_store.get("m1_bb_std", 1.2))
                                    self.bb_data["bb_length"] = bb_len
                                    self.bb_data["bb_std"] = bb_std_val
            except Exception as e:
                logger.error(f"Real-time loop: {e}")
                self.connected = False
            await asyncio.sleep(1)

    async def _seed(self, tf, engine):
        """Seed historical klines for MACD warmup"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10, verify=False) as c:
                r = await c.get("https://api.bitget.com/api/v2/spot/market/candles",
                                params={"symbol": self.pair, "granularity": tf, "limit": "200"})
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    for row in reversed(data):
                        if len(row) >= 5:
                            engine.update(float(row[4]))
                    logger.info(f"Seeded {len(data)} klines for {engine.label}")
        except Exception as e:
            logger.error(f"Seed {tf}: {e}")

    def get_analysis(self):
        m1 = self.m1.get_state()
        m5 = self.m5.get_state()
        m1a = m1["macd"] > 0
        m5a = m5["macd"] > 0
        aligned = (m1a and m5a) or (not m1a and not m5a)
        sig = "LONG" if m1a and m5a else "SHORT" if not m1a and not m5a else "NEUTRAL"
        return {"m1": m1, "m5": m5, "aligned": aligned, "trade_signal": sig,
                "timestamp": datetime.now().strftime("%H:%M:%S"), "price": self.price,
                "connected": self.connected, "last_tick": self.last_tick,
                "bb": self.bb_data, "ticker": self.ticker_data}

    def update_params(self, m1_fast, m1_slow, m1_sig, m5_fast, m5_slow, m5_sig, m1_source=None, m5_source=None):
        self.m1.fast = m1_fast; self.m1.slow = m1_slow; self.m1.signal = m1_sig
        self.m5.fast = m5_fast; self.m5.slow = m5_slow; self.m5.signal = m5_sig
        if m1_source: self.m1.source = m1_source
        if m5_source: self.m5.source = m5_source
        self.m1.reset(); self.m5.reset()
        logger.info(f"MACD params: M1({m1_fast}-{m1_slow}-{m1_sig}) M5({m5_fast}-{m5_slow}-{m5_sig})")

    async def update_pair(self, new_pair):
        """Change trading pair and re-seed"""
        if new_pair != self.pair:
            self.pair = new_pair
            self.price = 0.0
            self.connected = False
            self.m1.reset()
            self.m5.reset()
            await self._seed("1min", self.m1)
            await self._seed("5min", self.m5)
            logger.info(f"Pair changed to {new_pair}, re-seeded M1+M5")
