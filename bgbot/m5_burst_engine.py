"""
M5 BURST ENGINE - 1 Candle Momentum System
MACD 4-5-3 + Acceleration + Micro Breakout + M5 Context Filter
Ultra scalping: hold max 1 M5 candle (5 min)
"""
import time
import logging

logger = logging.getLogger("bgbot.m5burst")


class M5BurstEngine:
    """
    Entry: MACD crossover + momentum acceleration + micro breakout
    Exit: 1 M5 candle complete OR 80-100% M5 range OR stop loss
    """

    def __init__(self, fast=4, slow=5, signal=3):
        self.fast = fast
        self.slow = slow
        self.signal = signal

        # EMA alphas
        self.af = 2.0 / (fast + 1)
        self.asl = 2.0 / (slow + 1)
        self.asg = 2.0 / (signal + 1)

        # M1 state
        self.m1_ema_fast = None
        self.m1_ema_slow = None
        self.m1_ema_signal = 0.0
        self.m1_macd = 0.0
        self.m1_hist = 0.0
        self.m1_prev_hist = 0.0
        self.m1_prev_macd = 0.0
        self.m1_prev_signal = 0.0

        # M5 state
        self.m5_ema_fast = None
        self.m5_ema_slow = None
        self.m5_ema_signal = 0.0
        self.m5_macd = 0.0
        self.m5_hist = 0.0

        # Price tracking
        self.m1_prices = []
        self.m5_prices = []
        self.m1_highs = []
        self.m1_lows = []
        self.m5_highs = []
        self.m5_lows = []
        self.m5_ranges = []

        # Hist tracking for acceleration
        self.hist_buffer = []

        # Volatility
        self.volatility = 0.0
        self.last_price = None

        # State
        self.initialized = False
        self.tick_count = 0
        self.m5_candle_count = 0

        # Signal state
        self.last_signal = None
        self.last_signal_time = 0
        self.cooldown_sec = 60

    def reset(self):
        self.__init__(self.fast, self.slow, self.signal)

    def _init_m1(self, price):
        self.m1_ema_fast = price
        self.m1_ema_slow = price
        self.m1_ema_signal = 0.0
        self.m1_macd = 0.0
        self.m1_hist = 0.0

    def _init_m5(self, price):
        self.m5_ema_fast = price
        self.m5_ema_slow = price
        self.m5_ema_signal = 0.0
        self.m5_macd = 0.0
        self.m5_hist = 0.0

    def update_m1(self, price, high=None, low=None):
        """Feed M1 tick data"""
        price = float(price)
        if price <= 0:
            return

        if self.m1_ema_fast is None:
            self._init_m1(price)

        self.tick_count += 1

        # Track prices
        self.m1_prices.append(price)
        if len(self.m1_prices) > 100:
            self.m1_prices = self.m1_prices[-100:]

        if high:
            self.m1_highs.append(float(high))
            if len(self.m1_highs) > 20:
                self.m1_highs = self.m1_highs[-20:]
        if low:
            self.m1_lows.append(float(low))
            if len(self.m1_lows) > 20:
                self.m1_lows = self.m1_lows[-20:]

        # Volatility
        if self.last_price:
            change = abs(price - self.last_price)
            self.volatility = 0.9 * self.volatility + 0.1 * change
        self.last_price = price

        # Boost for low volatility
        boost = 1.0
        if self.volatility < price * 0.0005:
            boost = 1.4

        # EMA update
        self.m1_prev_macd = self.m1_macd
        self.m1_prev_signal = self.m1_ema_signal
        self.m1_prev_hist = self.m1_hist

        self.m1_ema_fast += self.af * (price - self.m1_ema_fast) * boost
        self.m1_ema_slow += self.asl * (price - self.m1_ema_slow) * boost
        self.m1_macd = self.m1_ema_fast - self.m1_ema_slow
        self.m1_ema_signal += self.asg * (self.m1_macd - self.m1_ema_signal)
        self.m1_hist = self.m1_macd - self.m1_ema_signal

        # Scale-aware recovery
        if abs(self.m1_hist) < 1e-6:
            scale = max(price * 0.000001, 0.0001)
            self.m1_hist = (price - self.m1_ema_slow) * scale

        # Minimum movement
        if self.m1_hist == 0.0:
            self.m1_hist = (price - self.m1_ema_slow) * 0.0002

        # Anti-spike
        if abs(self.m1_hist) > price * 0.01:
            self.m1_hist *= 0.6

        # Hist buffer for acceleration
        self.hist_buffer.append(self.m1_hist)
        if len(self.hist_buffer) > 10:
            self.hist_buffer = self.hist_buffer[-10:]

        self.initialized = True

    def update_m5(self, price, high=None, low=None):
        """Feed M5 candle data"""
        price = float(price)
        if price <= 0:
            return

        if self.m5_ema_fast is None:
            self._init_m5(price)

        self.m5_candle_count += 1

        # Track M5 prices
        self.m5_prices.append(price)
        if len(self.m5_prices) > 60:
            self.m5_prices = self.m5_prices[-60:]

        if high and low:
            self.m5_highs.append(float(high))
            self.m5_lows.append(float(low))
            self.m5_ranges.append(float(high) - float(low))
            if len(self.m5_highs) > 20:
                self.m5_highs = self.m5_highs[-20:]
                self.m5_lows = self.m5_lows[-20:]
                self.m5_ranges = self.m5_ranges[-20:]

        # EMA update
        self.m5_ema_fast += self.af * (price - self.m5_ema_fast)
        self.m5_ema_slow += self.asl * (price - self.m5_ema_slow)
        self.m5_macd = self.m5_ema_fast - self.m5_ema_slow
        self.m5_ema_signal += self.asg * (self.m5_macd - self.m5_ema_signal)
        self.m5_hist = self.m5_macd - self.m5_ema_signal

    def is_accelerating(self):
        """Check if histogram is accelerating (3 consecutive same direction)"""
        if len(self.hist_buffer) < 3:
            return False, "NEUTRAL"

        h = self.hist_buffer
        # Bullish acceleration: 3 rising positive
        if h[-1] > h[-2] > h[-3] and h[-1] > 0:
            return True, "BULL"
        # Bearish acceleration: 3 falling negative
        if h[-1] < h[-2] < h[-3] and h[-1] < 0:
            return True, "BEAR"
        return False, "NEUTRAL"

    def micro_breakout(self):
        """Check if price breaks micro high/low"""
        if len(self.m1_prices) < 5 or len(self.m1_highs) < 2:
            return False, False

        current = self.m1_prices[-1]
        prev_high = self.m1_highs[-2] if self.m1_highs else 0
        prev_low = self.m1_lows[-2] if self.m1_lows else float('inf')

        buy_break = current > prev_high if prev_high > 0 else False
        sell_break = current < prev_low if prev_low < float('inf') else False

        return buy_break, sell_break

    def m5_context_ok(self):
        """M5 energy filter - avoid overextended"""
        if len(self.m5_highs) < 5:
            return True  # Not enough data, allow

        total_range = max(self.m5_highs) - min(self.m5_lows) if self.m5_highs and self.m5_lows else 0
        recent_range = self.m5_highs[-1] - self.m5_lows[-1] if self.m5_highs and self.m5_lows else 0

        if total_range > 0 and recent_range > 0.7 * total_range:
            return False  # Overextended

        return True

    def macd_crossover(self):
        """Detect MACD line crossover signal line"""
        # Buy: MACD crosses above signal
        if self.m1_prev_macd < self.m1_prev_signal and self.m1_macd > self.m1_ema_signal:
            return "BUY"
        # Sell: MACD crosses below signal
        if self.m1_prev_macd > self.m1_prev_signal and self.m1_macd < self.m1_ema_signal:
            return "SELL"
        return None

    def hist_crossover(self):
        """Histogram zero-line crossover"""
        if self.m1_prev_hist <= 0 and self.m1_hist > 0:
            return "BUY"
        if self.m1_prev_hist >= 0 and self.m1_hist < 0:
            return "SELL"
        return None

    def generate_signal(self):
        """
        M5 BURST SIGNAL LOGIC:
        1. MACD M1 crossover (fresh)
        2. Histogram acceleration (momentum)
        3. Micro breakout (price confirmation)
        4. M5 context filter (energy check)
        5. Cooldown check
        """
        if not self.initialized:
            return None, "Not initialized"

        now = time.time()

        # Cooldown
        if now - self.last_signal_time < self.cooldown_sec:
            remaining = int(self.cooldown_sec - (now - self.last_signal_time))
            return None, f"Cooldown {remaining}s"

        # 1. MACD crossover
        cross = self.macd_crossover()
        hist_cross = self.hist_crossover()

        # Use either crossover type
        entry_type = cross or hist_cross
        if not entry_type:
            return None, "No crossover"

        # 2. Momentum acceleration
        accel, accel_dir = self.is_accelerating()
        if not accel:
            return None, f"No acceleration ({accel_dir})"

        # 3. Micro breakout
        buy_break, sell_break = self.micro_breakout()

        # 4. M5 context
        m5_ok = self.m5_context_ok()

        # 5. Volatility check
        vol_ok = self.volatility > 0.1

        # === BUY BURST ===
        if entry_type == "BUY" and accel_dir == "BULL":
            if buy_break and m5_ok and vol_ok:
                self.last_signal = "BUY"
                self.last_signal_time = now
                return "BUY", f"BUY BURST | MACD cross UP | Accel BULL | Break HIGH | Vol:{self.volatility:.2f}"
            reasons = []
            if not buy_break:
                reasons.append("no break")
            if not m5_ok:
                reasons.append("M5 overextended")
            if not vol_ok:
                reasons.append("low vol")
            return None, f"BUY setup but {', '.join(reasons)}"

        # === SELL BURST ===
        if entry_type == "SELL" and accel_dir == "BEAR":
            if sell_break and m5_ok and vol_ok:
                self.last_signal = "SELL"
                self.last_signal_time = now
                return "SELL", f"SELL BURST | MACD cross DOWN | Accel BEAR | Break LOW | Vol:{self.volatility:.2f}"
            reasons = []
            if not sell_break:
                reasons.append("no break")
            if not m5_ok:
                reasons.append("M5 overextended")
            if not vol_ok:
                reasons.append("low vol")
            return None, f"SELL setup but {', '.join(reasons)}"

        return None, f"Cross:{entry_type} Accel:{accel_dir} (no match)"

    def calc_exit(self, entry_price, side, m5_range=None):
        """
        Exit rules:
        - TP: 80-100% of M5 range OR fixed %
        - SL: Last M1 swing OR 0.3-0.5 M5 range
        """
        # Default M5 range
        if m5_range is None and self.m5_ranges:
            m5_range = self.m5_ranges[-1]
        if m5_range is None:
            m5_range = entry_price * 0.003  # 0.3% fallback

        if side == "BUY":
            tp = entry_price + (m5_range * 0.8)  # 80% M5 range
            sl = entry_price - (m5_range * 0.4)  # 40% M5 range
            # Swing low fallback
            if self.m1_lows:
                swing_sl = min(self.m1_lows[-5:]) if len(self.m1_lows) >= 5 else min(self.m1_lows)
                sl = max(sl, swing_sl)  # Use tighter of the two
        else:
            tp = entry_price - (m5_range * 0.8)
            sl = entry_price + (m5_range * 0.4)
            if self.m1_highs:
                swing_sl = max(self.m1_highs[-5:]) if len(self.m1_highs) >= 5 else max(self.m1_highs)
                sl = min(sl, swing_sl)

        return round(tp, 2), round(sl, 2)

    def check_exit(self, entry_price, side, current_price, candle_count):
        """
        Exit check:
        1. TP/SL hit
        2. 1 M5 candle complete (5 M1 candles)
        """
        if side == "BUY":
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price

        # Max 1 M5 candle = 5 M1 candles
        if candle_count >= 5:
            return True, f"1 M5 candle done ({candle_count}) | PnL: {pnl_pct*100:+.3f}%"

        # Quick profit (> 0.2% in < 3 candles)
        if pnl_pct > 0.002 and candle_count >= 2:
            return True, f"Quick profit {pnl_pct*100:+.3f}% in {candle_count} ticks"

        # Momentum reversal
        accel, accel_dir = self.is_accelerating()
        if side == "BUY" and accel and accel_dir == "BEAR":
            return True, f"Momentum reversed to BEAR | PnL: {pnl_pct*100:+.3f}%"
        if side == "SELL" and accel and accel_dir == "BULL":
            return True, f"Momentum reversed to BULL | PnL: {pnl_pct*100:+.3f}%"

        # Hard stop
        if pnl_pct < -0.003:
            return True, f"Hard stop {pnl_pct*100:+.3f}%"

        return False, f"Holding | PnL: {pnl_pct*100:+.3f}% | Candle: {candle_count}/5"

    def get_state(self):
        """Full state for dashboard"""
        accel, accel_dir = self.is_accelerating()
        price = self.m1_prices[-1] if self.m1_prices else 0

        return {
            "initialized": self.initialized,
            "tick_count": self.tick_count,
            "m5_candle_count": self.m5_candle_count,
            "price": price,
            "volatility": round(self.volatility, 4),
            # M1 MACD
            "m1_macd": round(self.m1_macd, 8),
            "m1_signal": round(self.m1_ema_signal, 8),
            "m1_hist": round(self.m1_hist, 8),
            "m1_prev_hist": round(self.m1_prev_hist, 8),
            "m1_bias": "BUY" if self.m1_hist > 0 else ("SELL" if self.m1_hist < 0 else "NEUTRAL"),
            # M5 MACD
            "m5_macd": round(self.m5_macd, 8),
            "m5_signal": round(self.m5_ema_signal, 8),
            "m5_hist": round(self.m5_hist, 8),
            "m5_bias": "BUY" if self.m5_hist > 0 else ("SELL" if self.m5_hist < 0 else "NEUTRAL"),
            # Momentum
            "accelerating": accel,
            "accel_direction": accel_dir,
            "momentum": "GROWING" if accel else ("FADING" if len(self.hist_buffer) >= 2 and abs(self.hist_buffer[-1]) < abs(self.hist_buffer[-2]) * 0.95 else "STABLE"),
            # Breakout
            "buy_break": self.micro_breakout()[0],
            "sell_break": self.micro_breakout()[1],
            # M5 context
            "m5_context_ok": self.m5_context_ok(),
            # Hist buffer
            "hist_buffer": [round(h, 8) for h in self.hist_buffer[-6:]],
            # Config
            "config": {"fast": self.fast, "slow": self.slow, "signal": self.signal},
        }
