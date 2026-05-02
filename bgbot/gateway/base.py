from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import pandas as pd


class ExchangeGateway(ABC):
    @abstractmethod
    def test(self) -> Dict[str, Any]: ...
    @abstractmethod
    def get_balance(self, market: str = "spot") -> float: ...
    @abstractmethod
    def get_klines(self, symbol: str, granularity: str, market: str = "spot", limit: int = 200) -> Optional[pd.DataFrame]: ...
    @abstractmethod
    def spot_market(self, symbol: str, side: str, size: float) -> Dict[str, Any]: ...
    @abstractmethod
    def spot_limit(self, symbol: str, side: str, price: float, size: float) -> Dict[str, Any]: ...
    @abstractmethod
    def perp_market(self, symbol: str, side: str, size: float, tp=None, sl=None) -> Dict[str, Any]: ...
    @abstractmethod
    def perp_limit(self, symbol: str, side: str, price: float, size: float, tp=None, sl=None) -> Dict[str, Any]: ...
    @abstractmethod
    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]: ...
    @abstractmethod
    def close_position(self, symbol: str, hold_side: str) -> Dict[str, Any]: ...
    @abstractmethod
    def set_leverage(self, symbol: str, leverage: int, hold_side: str) -> Dict[str, Any]: ...
    @abstractmethod
    def set_margin_mode(self, symbol: str, mode: str) -> Dict[str, Any]: ...
    @staticmethod
    @abstractmethod
    def fetch_historical(symbol: str, granularity: str, days: int = 7) -> Optional[pd.DataFrame]: ...


def get_exchange(name="bitget", api_key="", api_secret="", api_passphrase="", demo=True) -> ExchangeGateway:
    if name == "bitget":
        from gateway.bitget.client import BitgetClient
        return BitgetClient(api_key, api_secret, api_passphrase, demo)
    elif name == "binance":
        from gateway.binance.client import BinanceClient
        return BinanceClient(api_key, api_secret, demo)
    raise ValueError(f"Unknown exchange: {name}")
