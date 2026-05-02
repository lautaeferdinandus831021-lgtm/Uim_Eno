import pandas as pd


class RSI:
    def __init__(self, period=14):
        self.period = period

    def compute(self, df):
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=self.period, min_periods=self.period).mean()
        avg_loss = loss.rolling(window=self.period, min_periods=self.period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def compute_last(self, df):
        return float(self.compute(df).iloc[-1])

    def interpret(self, df):
        val = self.compute_last(df)
        if val > 70: return "OVERBOUGHT"
        elif val < 30: return "OVERSOLD"
        return "NEUTRAL"
