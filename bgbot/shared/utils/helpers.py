import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone


def api_retry(func, *args, retries=3, delay=1, **kwargs):
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                raise


class SimData:
    PRICES = {"BTCUSDT": 68420, "ETHUSDT": 3850, "SOLUSDT": 142, "BNBUSDT": 580, "XRPUSDT": 0.58, "DOGEUSDT": 0.12}

    @staticmethod
    def gen(symbol, minutes=200, interval=1):
        base = SimData.PRICES.get(symbol, 100)
        now = datetime.now(timezone.utc)
        price = base * (0.97 + np.random.random() * 0.06)
        candles = []
        for i in range(minutes):
            t = now - pd.Timedelta(minutes=(minutes - i) * interval)
            ch = np.random.normal(0, base * 0.0008)
            o, c = price, price + ch
            h = max(o, c) + abs(np.random.normal(0, base * 0.0003))
            l = min(o, c) - abs(np.random.normal(0, base * 0.0003))
            candles.append({"timestamp": t, "open": round(o, 2), "high": round(h, 2), "low": round(l, 2), "close": round(c, 2), "volume": round(abs(np.random.normal(100, 30)), 2)})
            price = c
        df = pd.DataFrame(candles)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
