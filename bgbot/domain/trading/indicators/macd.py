import math
import pandas as pd
from domain.trading.indicators.ema import EMA


class MACD:
    def __init__(self, fast=4, slow=5, signal=1):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal
        self._ema_fast = EMA(fast)
        self._ema_slow = EMA(slow)

    def compute(self, df, overlays=False):
        if len(df) < 3:
            return "NEUTRAL", None
        close = df["close"]
        ema_f = self._ema_fast.compute(close)
        ema_s = self._ema_slow.compute(close)
        macd_line = ema_f - ema_s
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        hist = macd_line - signal_line
        m_now = macd_line.iloc[-1]
        m_prev = macd_line.iloc[-2]
        s_now = signal_line.iloc[-1]
        s_prev = signal_line.iloc[-2]
        h_now = hist.iloc[-1]
        h_prev = hist.iloc[-2]
        cross_up = m_now > s_now and m_prev <= s_prev
        cross_down = m_now < s_now and m_prev >= s_prev
        if cross_up and h_now > h_prev:
            signal = "LONG"
        elif cross_down and h_now < h_prev:
            signal = "SHORT"
        elif m_now > s_now:
            signal = "LONG"
        elif m_now < s_now:
            signal = "SHORT"
        else:
            signal = "NEUTRAL"
        overlay_data = None
        if overlays:
            overlay_data = self._build_overlays(df, macd_line, signal_line, hist, ema_f, ema_s)
        return signal, overlay_data

    def compute_fast(self, df):
        signal, _ = self.compute(df, overlays=False)
        return signal

    def _build_overlays(self, df, macd_line, signal_line, hist, ema_f, ema_s):
        times = df["timestamp"].tolist()
        ml, sl, hl, ef, es = [], [], [], [], []
        for i, t in enumerate(times):
            ts = int(t.timestamp())
            if not math.isnan(macd_line.iloc[i]):
                hv = float(hist.iloc[i])
                ml.append({"time": ts, "value": round(float(macd_line.iloc[i]), 6)})
                sl.append({"time": ts, "value": round(float(signal_line.iloc[i]), 6)})
                hl.append({"time": ts, "value": round(hv, 6), "color": "rgba(0,212,170,0.6)" if hv >= 0 else "rgba(255,71,87,0.6)"})
                ef.append({"time": ts, "value": round(float(ema_f.iloc[i]), 2)})
                es.append({"time": ts, "value": round(float(ema_s.iloc[i]), 2)})
        return {"macd_line": ml, "macd_signal": sl, "macd_hist": hl, "ema_fast": ef, "ema_slow": es}
