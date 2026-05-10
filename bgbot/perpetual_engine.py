"""
Perpetual Bot Engine - WebSocket Real-Time + Orderbook Imbalance
BTCUSDT Hit & Run Strategy
"""
import asyncio
import json
import time
import hmac
import hashlib
import base64
import logging
from datetime import datetime
from m5_burst_engine import M5BurstEngine

logger = logging.getLogger("bgbot.perp")

try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


SYMBOL = "BTCUSDT_UMCBL"
BASE_URL = "https://api.bitget.com"
WS_URL = "wss://ws.bitget.com/mix/v1/stream"






class RealTimeMACD:
    """
    Production-Ready Real-Time MACD Engine
    - Tick-based EMA streaming (no batch)
    - Volatility boost engine (anti-flat)
    - Guaranteed histogram movement
    - Adaptive market sensitivity
    - Perfect for BTC perpetual scalping
    """

    def __init__(self, fast_period=4, slow_period=5, signal_period=3):
        self.af = 2.0 / (fast_period + 1)
        self.asl = 2.0 / (slow_period + 1)
        self.asg = 2.0 / (signal_period + 1)

        self.ema_fast = None
        self.ema_slow = None
        self.ema_signal = 0.0

        self.macd = 0.0
        self.hist = 0.0
        self.prev_hist = 0.0

        self.last_price = None
        self.volatility = 0.0
        self.last_update = 0

        self.initialized = False
        self.tick_count = 0

        # History for chart (last 60 points)
        self.macd_history = []
        self.signal_history = []
        self.hist_history = []
        self.price_history = []
        self.volatility_history = []

        # Peak/trough tracking
        self.peak_close = 0.0
        self.trough_close = float('inf')

    def _init(self, price):
        price = float(price)
        self.ema_fast = price
        self.ema_slow = price
        self.ema_signal = 0.0
        self.macd = 0.0
        self.hist = 0.0
        self.prev_hist = 0.0
        self.last_price = price
        self.peak_close = price
        self.trough_close = price
        self.initialized = True

    def _volatility_boost(self, price):
        """Anti-flat: boost in low volatility, dampen in extreme volatility"""
        if self.last_price is None:
            return 1.0

        change = abs(price - self.last_price)

        # Exponential moving volatility
        self.volatility = 0.9 * self.volatility + 0.1 * change

        # Low volatility → boost signal (price-scaled)
        if self.volatility < price * 0.0005:
            return 1.4

        # Extreme volatility → dampen noise
        if self.volatility > 50.0:
            return 0.7

        return 1.0

    def update(self, price):
        """Update MACD with new price tick. Returns (macd, histogram)"""
        try:
            price = float(price)
            if price <= 0:
                return self.macd, self.hist

            if not self.initialized:
                self._init(price)
                return self.macd, self.hist

            self.tick_count += 1
            boost = self._volatility_boost(price)

            # FAST EMA (tick-based with volatility boost)
            self.ema_fast += self.af * (price - self.ema_fast) * boost

            # SLOW EMA
            self.ema_slow += self.asl * (price - self.ema_slow) * boost

            # MACD LINE
            self.macd = self.ema_fast - self.ema_slow

            # SIGNAL LINE
            self.ema_signal += self.asg * (self.macd - self.ema_signal)

            # HISTOGRAM
            self.prev_hist = self.hist
            self.hist = self.macd - self.ema_signal

            # SAFE NON-ZERO HISTOGRAM RECOVERY (scale-aware)
            if abs(self.hist) < 1e-6:
                scale = max(price * 0.000001, 0.0001)
                self.hist = (price - self.ema_slow) * scale

            # FORCE MINIMUM MICRO MOVEMENT (anti-flat market bug)
            if self.hist == 0.0:
                self.hist = (price - self.last_price) * 0.0002

            # Anti-spike guard (BTC noise filter)
            if abs(self.hist) > price * 0.01:
                self.hist *= 0.6

            # Track peak/trough
            if price > self.peak_close:
                self.peak_close = price
            if price < self.trough_close:
                self.trough_close = price

            self.last_price = price
            self.last_update = time.time()

            # Store history (every 5 ticks to avoid memory bloat)
            if self.tick_count % 5 == 0:
                self.macd_history.append(round(self.macd, 8))
                self.signal_history.append(round(self.ema_signal, 8))
                self.hist_history.append(round(self.hist, 8))
                self.price_history.append(round(price, 2))
                self.volatility_history.append(round(self.volatility, 4))
                # Keep last 60 points
                if len(self.macd_history) > 60:
                    self.macd_history = self.macd_history[-60:]
                    self.signal_history = self.signal_history[-60:]
                    self.hist_history = self.hist_history[-60:]
                    self.price_history = self.price_history[-60:]
                    self.volatility_history = self.volatility_history[-60:]

            return self.macd, self.hist

        except Exception:
            return self.macd, self.hist

    def bias(self):
        """Current bias based on histogram"""
        if self.hist > 0:
            return "BUY"
        if self.hist < 0:
            return "SELL"
        return None

    def crossover(self):
        """
        Detect histogram zero-line crossover
        Returns: 'BUY', 'SELL', or None
        """
        if self.prev_hist <= 0 and self.hist > 0:
            return "BUY"
        if self.prev_hist >= 0 and self.hist < 0:
            return "SELL"
        return None

    def momentum(self):
        """Histogram momentum: growing or fading"""
        if abs(self.hist) > abs(self.prev_hist) * 1.05:
            return "GROWING"
        elif abs(self.hist) < abs(self.prev_hist) * 0.95:
            return "FADING"
        return "STABLE"

    def get_state(self):
        """Full state for dashboard"""
        price = self.last_price if self.last_price else (self.price_history[-1] if self.price_history else 0)
        pct_from_zero = (self.macd / price * 100) if price > 0 else 0
        hist_pct = (self.hist / price * 100) if price > 0 else 0

        bias = self.bias()
        cross = self.crossover()
        mom = self.momentum()

        if cross == "BUY":
            signal = "BUY"
        elif cross == "SELL":
            signal = "SELL"
        elif bias == "BUY":
            signal = "HOLD_LONG"
        elif bias == "SELL":
            signal = "HOLD_SHORT"
        else:
            signal = "WAIT"

        return {
            "macd": round(self.macd, 8),
            "signal_line": round(self.ema_signal, 8),
            "histogram": round(self.hist, 8),
            "prev_histogram": round(self.prev_hist, 8),
            "ema_fast": round(self.ema_fast, 2),
            "ema_slow": round(self.ema_slow, 2),
            "signal": "LONG" if self.hist > 0 else ("SHORT" if self.hist < 0 else "NEUTRAL"),
            "buy_sell": signal,
            "bias": bias,
            "crossover": cross,
            "momentum": mom,
            "volatility": round(self.volatility, 4),
            "macd_pct_from_zero": round(pct_from_zero, 8),
            "hist_pct_from_zero": round(hist_pct, 8),
            "signal_line_pct": round((self.ema_signal / price * 100) if price > 0 else 0, 8),
            "macd_history": self.macd_history[-60:],
            "signal_history": self.signal_history[-60:],
            "hist_history": self.hist_history[-60:],
            "close_history": self.price_history[-60:],
            "volatility_history": self.volatility_history[-60:],
            "candles": self.tick_count,
            "price": price,
            "peak_close": self.peak_close,
            "trough_close": self.trough_close if self.trough_close != float('inf') else 0,
            "config": {"fast": 4, "slow": 5, "signal": 3},
        }

    def reset(self):
        """Reset all state"""
        self.ema_fast = None
        self.ema_slow = None
        self.ema_signal = 0.0
        self.macd = 0.0
        self.hist = 0.0
        self.prev_hist = 0.0
        self.last_price = None
        self.volatility = 0.0
        self.last_update = 0
        self.initialized = False
        self.tick_count = 0
        self.macd_history = []
        self.signal_history = []
        self.hist_history = []
        self.price_history = []
        self.volatility_history = []
        self.peak_close = 0.0
        self.trough_close = float('inf')




def f(x):
    try:
        return float(x)
    except:
        return 0.0


def ts_ms():
    return str(int(time.time() * 1000))


def sign_msg(secret, msg):
    return base64.b64encode(
        hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()


def make_headers(api_key, api_secret, passphrase, method, path, body=""):
    t = ts_ms()
    msg = t + method.upper() + path + body
    return {
        "ACCESS-KEY": api_key,
        "ACCESS-SIGN": sign_msg(api_secret, msg),
        "ACCESS-TIMESTAMP": t,
        "ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }


class PerpState:
    """Thread-safe state for perpetual bot"""
    def __init__(self):
        self.price = 0.0
        self.prev_close = None
        self.candle_o = 0.0
        self.candle_c = 0.0
        self.imbalance = 0.0
        self.spread = 0.0
        self.bid_vol = 0.0
        self.ask_vol = 0.0
        self.best_bid = 0.0
        self.best_ask = 0.0
        self.direction = None
        self.entry_price = 0.0
        self.candle_count = 0
        self.running = False
        self.logs = []
        self.stats = {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0}
        self.last_signal = "WAIT"
        self.ws_connected = False
        # M5 Burst Engine
        self.burst_engine = None

        # MACD streaming instances
        self.macd_m1 = None
        self.macd_m5 = None

    def log(self, msg, pnl=0.0):
        entry = {"time": datetime.now().strftime("%H:%M:%S"), "msg": msg, "pnl": pnl}
        self.logs.append(entry)
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]
        logger.info(f"PerpBot: {msg}")

    def calc_imbalance(self, bids, asks):
        try:
            bid_v = sum(f(b[1]) for b in bids[:5] if len(b) >= 2)
            ask_v = sum(f(a[1]) for a in asks[:5] if len(a) >= 2)
            denom = bid_v + ask_v + 1e-9
            self.bid_vol = bid_v
            self.ask_vol = ask_v
            return (bid_v - ask_v) / denom
        except:
            return 0.0


def risk_check(state):
    if state.spread > 80:
        return False, "Spread too wide"
    if abs(state.imbalance) < 0.05:
        return False, "Imbalance too low"
    return True, "OK"


def generate_signal(state):
    if state.prev_close is None or state.candle_c == 0:
        return None, "No prev close"

    move = (state.candle_c - state.prev_close) / state.prev_close

    if move > 0.002 and state.imbalance > 0.1:
        return "BUY", f"Move +{move*100:.3f}% Imbalance +{state.imbalance:.3f}"
    if move < -0.002 and state.imbalance < -0.1:
        return "SELL", f"Move {move*100:.3f}% Imbalance {state.imbalance:.3f}"
    return None, f"Move {move*100:.3f}% Imbal {state.imbalance:.3f}"


def check_exit(state):
    if state.direction is None:
        return False, ""

    move = (state.price - state.entry_price) / state.entry_price

    if state.direction == "BUY":
        if move > 0.003:
            return True, f"TP hit +{move*100:.3f}%"
        if move < -0.002:
            return True, f"SL hit {move*100:.3f}%"
    if state.direction == "SELL":
        if move < -0.003:
            return True, f"TP hit {move*100:.3f}%"
        if move > 0.002:
            return True, f"SL hit +{move*100:.3f}%"

    if state.candle_count >= 3:
        return True, f"Max candles ({state.candle_count})"

    return False, ""


async def place_perp_order(api_key, api_secret, passphrase, side, price, size=0.001):
    """Place perpetual limit order"""
    path = "/api/v2/mix/order/place-order"
    url = BASE_URL + path
    body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginMode": "crossed",
        "marginCoin": "USDT",
        "side": side.lower(),
        "orderType": "limit",
        "price": str(round(price, 2)),
        "size": str(size),
        "timeInForceValue": "normal",
        "reduceOnly": "false",
    }
    body_str = json.dumps(body)
    hdrs = make_headers(api_key, api_secret, passphrase, "POST", path, body_str)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, content=body_str, headers=hdrs, timeout=10)
            result = resp.json()
            if result.get("code") == "00000":
                return {"ok": True, "order_id": result.get("data", {}).get("orderId", "")}
            return {"ok": False, "error": result.get("msg", "Unknown")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def close_perp_order(api_key, api_secret, passphrase, side, price, size=0.001):
    """Close perpetual position with limit order"""
    path = "/api/v2/mix/order/place-order"
    url = BASE_URL + path
    body = {
        "symbol": "BTCUSDT",
        "productType": "USDT-FUTURES",
        "marginMode": "crossed",
        "marginCoin": "USDT",
        "side": side.lower(),
        "orderType": "limit",
        "price": str(round(price, 2)),
        "size": str(size),
        "timeInForceValue": "normal",
        "reduceOnly": "true",
    }
    body_str = json.dumps(body)
    hdrs = make_headers(api_key, api_secret, passphrase, "POST", path, body_str)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, content=body_str, headers=hdrs, timeout=10)
            result = resp.json()
            if result.get("code") == "00000":
                return {"ok": True, "order_id": result.get("data", {}).get("orderId", "")}
            return {"ok": False, "error": result.get("msg", "Unknown")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def ws_ticker(state):
    """WebSocket ticker stream"""
    while state.running:
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10) as ws:
                subscribe = {"op": "subscribe", "args": [{"instType": "USDT-FUTURES", "channel": "ticker", "instId": "BTCUSDT"}]}
                await ws.send(json.dumps(subscribe))
                state.ws_connected = True
                logger.info("PerpBot WS Ticker connected")

                while state.running:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30)
                    data = json.loads(msg)
                    if data.get("action") == "snapshot" or data.get("event") == "subscribe":
                        continue
                    arg = data.get("arg", {})
                    if arg.get("channel") == "ticker":
                        d = data.get("data", [{}])
                        if d and isinstance(d, list):
                            state.price = f(d[0].get("lastPr", 0))
                            # Feed tick price to MACD M5
                            if state.macd_m5 and state.price > 0:
                                state.macd_m5.update(state.price)
                            # Feed to burst engine M5
                            if state.burst_engine and state.price > 0:
                                state.burst_engine.update_m5(state.price)
        except Exception as e:
            state.ws_connected = False
            logger.warning(f"WS Ticker reconnect: {e}")
            await asyncio.sleep(2)


async def ws_candle(state):
    """WebSocket candle stream (1min)"""
    while state.running:
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10) as ws:
                subscribe = {"op": "subscribe", "args": [{"instType": "USDT-FUTURES", "channel": "candle1m", "instId": "BTCUSDT"}]}
                await ws.send(json.dumps(subscribe))

                while state.running:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30)
                    data = json.loads(msg)
                    arg = data.get("arg", {})
                    if arg.get("channel") == "candle1m":
                        d = data.get("data", [])
                        if d and isinstance(d, list) and len(d[0]) >= 5:
                            c = d[0]
                            state.candle_o = f(c[1])
                            state.candle_c = f(c[4])
                            # Feed close price to MACD M1
                            if state.macd_m1 and state.candle_c > 0:
                                state.macd_m1.update(state.candle_c)
                            # Feed to burst engine
                            if state.burst_engine and state.candle_c > 0:
                                state.burst_engine.update_m1(state.candle_c, state.candle_o if hasattr(state, 'candle_o') else None, None)
        except Exception as e:
            logger.warning(f"WS Candle reconnect: {e}")
            await asyncio.sleep(2)


async def ws_orderbook(state):
    """WebSocket orderbook stream"""
    while state.running:
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10) as ws:
                subscribe = {"op": "subscribe", "args": [{"instType": "USDT-FUTURES", "channel": "books5", "instId": "BTCUSDT"}]}
                await ws.send(json.dumps(subscribe))

                while state.running:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30)
                    data = json.loads(msg)
                    arg = data.get("arg", {})
                    if arg.get("channel") == "books5":
                        d = data.get("data", [])
                        if d and isinstance(d, list):
                            ob = d[0]
                            bids = ob.get("bids", [])
                            asks = ob.get("asks", [])
                            state.imbalance = state.calc_imbalance(bids, asks)
                            if bids and asks:
                                state.best_bid = f(bids[0][0])
                                state.best_ask = f(asks[0][0])
                                state.spread = state.best_ask - state.best_bid
        except Exception as e:
            logger.warning(f"WS Orderbook reconnect: {e}")
            await asyncio.sleep(2)


async def engine_loop(state, api_key="", api_secret="", passphrase="", use_real_orders=False):
    """Main trading engine loop"""
    while state.running:
        try:
            if state.price == 0 or state.candle_c == 0:
                await asyncio.sleep(0.1)
                continue

            # Check exit first
            if state.direction is not None:
                should_exit = False
                exit_reason = ""

                # M5 Burst exit (primary)
                if state.burst_engine and state.burst_engine.initialized:
                    burst_exit, burst_reason = state.burst_engine.check_exit(
                        state.entry_price, state.direction, state.price, state.candle_count
                    )
                    if burst_exit:
                        should_exit = True
                        exit_reason = f"BURST: {burst_reason}"

                # Fallback: standard exit
                if not should_exit:
                    should_exit, exit_reason = check_exit(state)

                # MACD crossover exit
                if not should_exit:
                    m5_cross = state.macd_m5.crossover() if state.macd_m5 else None
                    if state.direction == "BUY" and m5_cross == "SELL":
                        should_exit = True
                        exit_reason = "MACD reverse SELL"
                    elif state.direction == "SELL" and m5_cross == "BUY":
                        should_exit = True
                        exit_reason = "MACD reverse BUY"
                if should_exit:
                    pnl = 0
                    if state.direction == "BUY":
                        pnl = (state.price - state.entry_price) * 0.001
                    else:
                        pnl = (state.entry_price - state.price) * 0.001

                    if use_real_orders and api_key:
                        close_side = "sell" if state.direction == "BUY" else "buy"
                        result = await close_perp_order(api_key, api_secret, passphrase, close_side, state.price, 0.001)
                        state.log(f"EXIT {state.direction} @ ${state.price:,.2f} | {exit_reason} | PnL: ${pnl:+.2f} | Order: {result}", pnl)
                    else:
                        state.log(f"EXIT {state.direction} @ ${state.price:,.2f} | {exit_reason} | PnL: ${pnl:+.2f} (DEMO)", pnl)

                    state.stats["trades"] += 1
                    state.stats["pnl"] += pnl
                    if pnl > 0:
                        state.stats["wins"] += 1
                    else:
                        state.stats["losses"] += 1

                    state.direction = None
                    state.entry_price = 0
                    state.candle_count = 0
                    state.last_signal = "WAIT"

                else:
                    state.candle_count += 1
                    move = (state.price - state.entry_price) / state.entry_price
                    m1_data = state.macd_m1.get_state() if state.macd_m1 else {}
                    m5_data = state.macd_m5.get_state() if state.macd_m5 else {}
                    m1_info = f"M1={m1_data.get('buy_sell','?')}({m1_data.get('histogram',0):.6f})" if m1_data else ""
                    m5_info = f"M5={m5_data.get('buy_sell','?')}({m5_data.get('histogram',0):.6f})" if m5_data else ""
                    state.log(f"HOLD {state.direction} @ ${state.entry_price:,.2f} | Now: ${state.price:,.2f} | Move: {move*100:+.3f}% | {m1_info} {m5_info}")

            # Check entry using M5 BURST + MACD
            if state.direction is None:
                sig = None
                sig_reason = ""

                # Try M5 Burst Engine first (primary signal)
                if state.burst_engine and state.burst_engine.initialized:
                    burst_sig, burst_reason = state.burst_engine.generate_signal()
                    if burst_sig:
                        sig = burst_sig
                        sig_reason = f"BURST: {burst_reason}"

                # Fallback: MACD crossover
                if not sig:
                    m5_cross = state.macd_m5.crossover() if state.macd_m5 else None
                    m1_bias = state.macd_m1.bias() if state.macd_m1 else None
                    m5_bias = state.macd_m5.bias() if state.macd_m5 else None

                    if m5_cross == "BUY":
                        sig = "BUY"
                        sig_reason = f"MACD crossover BUY | M1: {m1_bias}"
                    elif m5_cross == "SELL":
                        sig = "SELL"
                        sig_reason = f"MACD crossover SELL | M1: {m1_bias}"
                    elif m1_bias and m5_bias and m1_bias == m5_bias:
                        ok, risk_reason = risk_check(state)
                        if ok:
                            orig_sig, orig_reason = generate_signal(state)
                            if orig_sig:
                                sig = orig_sig
                                sig_reason = f"Orderbook {orig_sig} | {orig_reason}"

                state.last_signal = sig if sig else "WAIT"

                if sig:
                        state.direction = sig
                        state.entry_price = state.price
                        state.candle_count = 0

                        m1_data = state.macd_m1.get_state() if state.macd_m1 else {}
                        m5_data = state.macd_m5.get_state() if state.macd_m5 else {}
                        m1_info = f"M1={m1_data.get('buy_sell','?')}({m1_data.get('histogram',0):.6f})" if m1_data else "M1=N/A"
                        m5_info = f"M5={m5_data.get('buy_sell','?')}({m5_data.get('histogram',0):.6f})" if m5_data else "M5=N/A"

                        if use_real_orders and api_key:
                            result = await place_perp_order(api_key, api_secret, passphrase, sig, state.price, 0.001)
                            state.log(f"ENTRY {sig} @ ${state.price:,.2f} | {sig_reason} | {m1_info} {m5_info} | Order: {result}")
                        else:
                            state.log(f"ENTRY {sig} @ ${state.price:,.2f} | {sig_reason} | {m1_info} {m5_info} (DEMO)")
                else:
                    state.last_signal = f"BLOCKED: {risk_reason}"

            state.prev_close = state.candle_c
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Engine error: {e}")
            await asyncio.sleep(1)


# Global instance
perp_state = PerpState()
perp_tasks = []


async def start_perp_bot(api_key="", api_secret="", passphrase="", use_real=False,
    m1_fast=4, m1_slow=5, m1_sig=3, m5_fast=4, m5_slow=5, m5_sig=3):
    global perp_tasks
    if perp_state.running:
        return {"ok": False, "msg": "Already running"}

    perp_state.running = True
    perp_state.logs = []
    perp_state.stats = {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0}
    perp_state.direction = None
    perp_state.entry_price = 0
    perp_state.candle_count = 0
    perp_state.prev_close = None

    # Initialize streaming MACD with CONFIG params
    perp_state.macd_m1 = RealTimeMACD(fast_period=m1_fast, slow_period=m1_slow, signal_period=m1_sig)
    perp_state.macd_m5 = RealTimeMACD(fast_period=m5_fast, slow_period=m5_slow, signal_period=m5_sig)
    # Initialize M5 Burst Engine with CONFIG params
    perp_state.burst_engine = M5BurstEngine(fast=m5_fast, slow=m5_slow, signal=m5_sig)
    logger.info(f"PerpBot MACD: M1({m1_fast}-{m1_slow}-{m1_sig}) M5({m5_fast}-{m5_slow}-{m5_sig})")

    if HAS_WS:
        perp_tasks = [
            asyncio.create_task(ws_ticker(perp_state)),
            asyncio.create_task(ws_candle(perp_state)),
            asyncio.create_task(ws_orderbook(perp_state)),
            asyncio.create_task(engine_loop(perp_state, api_key, api_secret, passphrase, use_real)),
        ]
        perp_state.log(f"PerpBot started (WebSocket) | Real orders: {use_real}")
    else:
        # Fallback: polling mode
        perp_state.log("WebSocket not available, using polling mode")
        perp_tasks = [
            asyncio.create_task(engine_loop(perp_state, api_key, api_secret, passphrase, use_real)),
        ]

    return {"ok": True, "msg": "PerpBot started"}


async def stop_perp_bot():
    global perp_tasks
    perp_state.running = False
    for t in perp_tasks:
        t.cancel()
    perp_tasks = []

    if perp_state.direction:
        perp_state.log(f"Bot stopped with open {perp_state.direction} position")
    else:
        perp_state.log("Bot stopped")

    perp_state.direction = None
    perp_state.entry_price = 0
    if perp_state.macd_m1:
        perp_state.macd_m1.reset()
    if perp_state.macd_m5:
        perp_state.macd_m5.reset()
    if perp_state.burst_engine:
        perp_state.burst_engine.reset()
    return {"ok": True, "msg": "PerpBot stopped"}


def get_perp_status():
    # Get MACD state
    m1_state = perp_state.macd_m1.get_state() if perp_state.macd_m1 and perp_state.macd_m1.initialized else {"signal": "INIT", "buy_sell": "WAIT", "volatility": 0}
    m5_state = perp_state.macd_m5.get_state() if perp_state.macd_m5 and perp_state.macd_m5.initialized else {"signal": "INIT", "buy_sell": "WAIT", "volatility": 0}
    burst_state = perp_state.burst_engine.get_state() if perp_state.burst_engine and perp_state.burst_engine.initialized else {}

    return {
        "running": perp_state.running,
        "ws_connected": perp_state.ws_connected,
        "price": perp_state.price,
        "spread": round(perp_state.spread, 2),
        "imbalance": round(perp_state.imbalance, 6),
        "bid_vol": round(perp_state.bid_vol, 4),
        "ask_vol": round(perp_state.ask_vol, 4),
        "best_bid": round(perp_state.best_bid, 2),
        "best_ask": round(perp_state.best_ask, 2),
        "direction": perp_state.direction,
        "entry_price": perp_state.entry_price,
        "candle_count": perp_state.candle_count,
        "last_signal": perp_state.last_signal,
        "stats": perp_state.stats,
        "logs": perp_state.logs[-30:],
        "burst": burst_state,
        "m1": m1_state,
        "m5": m5_state,
    }
