import pandas as pd


class EMA:
    def __init__(self, period: int):
        self.period = period

    def compute(self, series: pd.Series) -> pd.Series:
        return series.ewm(span=self.period, adjust=False).mean()

    def compute_last(self, series: pd.Series) -> float:
        return float(self.compute(series).iloc[-1])
