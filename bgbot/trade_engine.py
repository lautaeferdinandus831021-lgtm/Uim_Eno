"""
MACD Strategy Engine - Real-Time Streaming + Batch Hybrid
Spot: batch MACD from candle data
Perpetual: streaming RealTimeMACD
Signal period = 3 (not 1) for proper histogram range
"""
import logging
import time
from datetime import datetime

logger = logging.getLogger("bgbot.engine")


class RealTimeMACD:
    """
    Production-Ready Real-Time MACD Engine
    - Tick-based EMA streaming
    - Volatility boost engine (anti-flat)
    - Guaranteed histogram movement
    - Adaptive market sensitivity
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

        self.macd_history = []
        self.signal_history = []
        self.hist_history = []
        self.price_history = []
        self.volatility_history = []

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
        if self.last_price is None:
            return 1.0
        change = abs(price - self.last_price)
        self.volatility = 0.9 * self.volatility + 0.1 * change
        if self.volatility < price * 0.0005:
            return 1.4
        if self.volatility > 50.0:
            return 0.7
        return 1.0

    def update(self, price):
        try:
            price = float(price)
            if price <= 0:
                return self.macd, self.hist

            if not self.initialized:
                self._init(price)
                return self.macd, self.hist

            self.tick_count += 1
            boost = self._volatility_boost(price)

            self.ema_fast += self.af * (price - self.ema_fast) * boost
            self.ema_slow += self.asl * (price - self.ema_slow) * boost
            self.macd = self.ema_fast - self.ema_slow
            self.ema_signal += self.asg * (self.macd - self.ema_signal)

            self.prev_hist = self.hist
            self.hist = self.macd - self.ema_signal

            # Scale-aware histogram recovery
            if abs(self.hist) < 1e-6:
                scale = max(price * 0.000001, 0.0001)
                self.hist = (price - self.ema_slow) * scale

            # Minimum micro movement
            if self.hist == 0.0:
                self.hist = (price - self.last_price) * 0.0002

            # Anti-spike guard
            if abs(self.hist) > price * 0.01:
                self.hist *= 0.6

            if price > self.peak_close:
                self.peak_close = price
            if price < self.trough_close:
                self.trough_close = price

            self.last_price = price
            self.last_update = time.time()

            if self.tick_count % 5 == 0:
                self.macd_history.append(round(self.macd, 8))
                self.signal_history.append(round(self.ema_signal, 8))
                self.hist_history.append(round(self.hist, 8))
                self.price_history.append(round(price, 2))
                self.volatility_history.append(round(self.volatility, 4))
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
        if self.hist > 0:
            return "BUY"
        if self.hist < 0:
            return "SELL"
        return None

    def crossover(self):
        if self.prev_hist <= 0 and self.hist > 0:
            return "BUY"
        if self.prev_hist >= 0 and self.hist < 0:
            return "SELL"
        return None

    def momentum(self):
        if abs(self.hist) > abs(self.prev_hist) * 1.05:
            return "GROWING"
        elif abs(self.hist) < abs(self.prev_hist) * 0.95:
            return "FADING"
        return "STABLE"

    def get_state(self):
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
            "ema_fast": round(self.ema_fast, 2) if self.ema_fast else 0,
            "ema_slow": round(self.ema_slow, 2) if self.ema_slow else 0,
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


def calc_ema(values, period):
    if not values or period <= 0:
        return 0.0
    if len(values) < period:
        return sum(values) / len(values)
    ema = sum(values[:period]) / period
    k = 2.0 / (period + 1)
    for price in values[period:]:
        ema = price * k + ema * (1 - k)
    return ema


def calc_macd_series(closes, fast=4, slow=5, signal_period=3):
    """Calculate full MACD series from close prices (batch mode for spot)."""
    min_len = slow + signal_period + 10
    if not closes or len(closes) < min_len:
        return {
            "macd": 0.0, "signal_line": 0.0, "histogram": 0.0,
            "signal": "NEUTRAL", "buy_sell": "WAIT",
            "ema_fast": 0.0, "ema_slow": 0.0,
            "macd_pct_from_zero": 0.0, "hist_pct_from_zero": 0.0, "signal_line_pct": 0.0,
            "macd_history": [], "signal_history": [], "hist_history": [],
            "close_history": [], "candles": len(closes),
            "peak_close": 0.0, "trough_close": 0.0,
            "momentum": "N/A", "volatility": 0.0,
            "config": {"fast": fast, "slow": slow, "signal": signal_period},
        }

    macd_series = []
    for i in range(slow, len(closes)):
        subset = closes[:i + 1]
        ef = calc_ema(subset, fast)
        es = calc_ema(subset, slow)
        macd_series.append(ef - es)

    signal_series = []
    for i in range(signal_period, len(macd_series)):
        subset = macd_series[:i + 1]
        signal_series.append(calc_ema(subset, signal_period))

    offset = len(macd_series) - len(signal_series)
    hist_series = []
    for i in range(len(signal_series)):
        hist_series.append(macd_series[offset + i] - signal_series[i])

    current_macd = macd_series[-1] if macd_series else 0.0
    current_signal = signal_series[-1] if signal_series else 0.0
    current_hist = hist_series[-1] if hist_series else 0.0
    current_price = closes[-1]
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)

    macd_pct = (current_macd / current_price * 100) if current_price else 0.0
    hist_pct = (current_hist / current_price * 100) if current_price else 0.0
    signal_pct = (current_signal / current_price * 100) if current_price else 0.0

    buy_sell = "WAIT"
    peak_close = 0.0
    trough_close = 0.0
    momentum = "N/A"

    if len(hist_series) >= 2:
        prev_hist = hist_series[-2]
        curr_hist = hist_series[-1]

        if prev_hist <= 0 and curr_hist > 0:
            buy_sell = "BUY"
        elif prev_hist >= 0 and curr_hist < 0:
            buy_sell = "SELL"
        elif curr_hist > 0:
            buy_sell = "HOLD_LONG"
        elif curr_hist < 0:
            buy_sell = "HOLD_SHORT"

        # Momentum
        if abs(curr_hist) > abs(prev_hist) * 1.05:
            momentum = "GROWING"
        elif abs(curr_hist) < abs(prev_hist) * 0.95:
            momentum = "FADING"
        else:
            momentum = "STABLE"

        # Peak/trough
        if curr_hist > 0:
            streak_start = len(hist_series) - 1
            for i in range(len(hist_series) - 1, -1, -1):
                if hist_series[i] > 0:
                    streak_start = i
                else:
                    break
            close_streak_start = slow + signal_period + streak_start
            if close_streak_start < len(closes):
                peak_close = max(closes[close_streak_start:])
            else:
                peak_close = current_price
        elif curr_hist < 0:
            streak_start = len(hist_series) - 1
            for i in range(len(hist_series) - 1, -1, -1):
                if hist_series[i] < 0:
                    streak_start = i
                else:
                    break
            close_streak_start = slow + signal_period + streak_start
            if close_streak_start < len(closes):
                trough_close = min(closes[close_streak_start:])
            else:
                trough_close = current_price

    if current_hist > 0:
        signal = "LONG"
    elif current_hist < 0:
        signal = "SHORT"
    else:
        signal = "NEUTRAL"

    chart_len = 60
    macd_chart = [round(v, 8) for v in macd_series[-chart_len:]]
    signal_chart = [round(v, 8) for v in signal_series[-chart_len:]]
    hist_chart = [round(v, 8) for v in hist_series[-chart_len:]]
    close_chart = [round(v, 2) for v in closes[-chart_len:]]

    max_len = max(len(macd_chart), len(signal_chart), len(hist_chart))
    while len(macd_chart) < max_len:
        macd_chart.insert(0, 0.0)
    while len(signal_chart) < max_len:
        signal_chart.insert(0, 0.0)
    while len(hist_chart) < max_len:
        hist_chart.insert(0, 0.0)

    return {
        "macd": round(current_macd, 8),
        "signal_line": round(current_signal, 8),
        "histogram": round(current_hist, 8),
        "signal": signal,
        "buy_sell": buy_sell,
        "ema_fast": round(ema_fast, 2),
        "ema_slow": round(ema_slow, 2),
        "macd_pct_from_zero": round(macd_pct, 8),
        "hist_pct_from_zero": round(hist_pct, 8),
        "signal_line_pct": round(signal_pct, 8),
        "macd_history": macd_chart,
        "signal_history": signal_chart,
        "hist_history": hist_chart,
        "close_history": close_chart,
        "candles": len(closes),
        "peak_close": round(peak_close, 2),
        "trough_close": round(trough_close, 2),
        "momentum": momentum,
        "volatility": 0.0,
        "config": {"fast": fast, "slow": slow, "signal": signal_period},
    }


def analyze_timeframe(closes, tf_config):
    fast = tf_config.get("fast", 4)
    slow = tf_config.get("slow", 5)
    signal_p = tf_config.get("signal", 3)
    result = calc_macd_series(closes, fast, slow, signal_p)
    result["price"] = closes[-1] if closes else 0
    return result


def analyze_m1_m5(closes_m1, closes_m5, config):
    m1_cfg = config.get("m1", {"fast": 4, "slow": 5, "signal": 3})
    m5_cfg = config.get("m5", {"fast": 4, "slow": 5, "signal": 3})

    m1 = analyze_timeframe(closes_m1, m1_cfg)
    m5 = analyze_timeframe(closes_m5, m5_cfg)

    m1_above_zero = m1["macd"] > 0
    m1_below_zero = m1["macd"] < 0
    m5_above_zero = m5["macd"] > 0
    m5_below_zero = m5["macd"] < 0

    aligned = False
    trade_signal = "NEUTRAL"

    if m1_above_zero and m5_above_zero:
        aligned = True
        trade_signal = "LONG"
    elif m1_below_zero and m5_below_zero:
        aligned = True
        trade_signal = "SHORT"
    elif m1_above_zero and m5["histogram"] > 0 and not m5_above_zero:
        aligned = False
        trade_signal = "PENDING_LONG"
    elif m1_below_zero and m5["histogram"] < 0 and not m5_below_zero:
        aligned = False
        trade_signal = "PENDING_SHORT"
    else:
        aligned = False
        trade_signal = "NEUTRAL"

    return {
        "m1": m1,
        "m5": m5,
        "aligned": aligned,
        "trade_signal": trade_signal,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


def should_trade(analysis, current_price, config, has_position=False):
    if not analysis["aligned"]:
        m1 = analysis.get("m1", {})
        m5 = analysis.get("m5", {})
        m1_pos = "ABOVE" if m1.get("macd", 0) > 0 else "BELOW"
        m5_pos = "ABOVE" if m5.get("macd", 0) > 0 else "BELOW"
        m5_bs = m5.get("buy_sell", "WAIT")
        return False, f"Not aligned | M1 {m1_pos} zero | M5 {m5_pos} zero | M5 signal: {m5_bs}"

    signal = analysis["trade_signal"]
    if signal == "NEUTRAL":
        return False, "Neutral"
    if has_position:
        return False, "Already in position"

    m1 = analysis["m1"]
    m5 = analysis["m5"]

    m5_bs = m5.get("buy_sell", "WAIT")
    if signal == "LONG" and m5_bs not in ("BUY", "HOLD_LONG"):
        return False, f"M5 not ready for LONG | M5: {m5_bs}"
    if signal == "SHORT" and m5_bs not in ("SELL", "HOLD_SHORT"):
        return False, f"M5 not ready for SHORT | M5: {m5_bs}"

    return True, f"{signal} | M1={m1['macd']:.6f} | M5={m5['macd']:.6f} | M5 signal: {m5_bs}"


def calc_tp_sl(entry_price, side, config, m5_analysis=None):
    tp_pct = config.get("tp_percent", 2.5) / 100
    sl_pct = config.get("sl_percent", 1.5) / 100

    if side == "LONG":
        if m5_analysis and m5_analysis.get("peak_close", 0) > entry_price:
            tp = m5_analysis["peak_close"]
        else:
            tp = entry_price * (1 + tp_pct)
        sl = entry_price * (1 - sl_pct)
    else:
        if m5_analysis and m5_analysis.get("trough_close", 0) > 0 and m5_analysis["trough_close"] < entry_price:
            tp = m5_analysis["trough_close"]
        else:
            tp = entry_price * (1 - tp_pct)
        sl = entry_price * (1 + sl_pct)

    return round(tp, 2), round(sl, 2)
