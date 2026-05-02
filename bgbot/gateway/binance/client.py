import logging
from typing import Optional, List, Dict, Any
import pandas as pd
from gateway.base import ExchangeGateway

logger = logging.getLogger("bgbot.binance")


class BinanceClient(ExchangeGateway):
    BASE = "https://api.binance.com"

    def __init__(self, key="", secret="", demo=True):
        self.key, self.secret, self.demo = key, secret, demo

    def test(self):
        return {"ok": False, "msg": "Binance not implemented yet"}
    def get_balance(self, market="spot"):
        return 0
    def get_klines(self, symbol, granularity, market="spot", limit=200):
        return None
    def spot_market(self, symbol, side, size):
        return {"code": "99999", "msg": "Not implemented"}
    def spot_limit(self, symbol, side, price, size):
        return {"code": "99999", "msg": "Not implemented"}
    def perp_market(self, symbol, side, size, tp=None, sl=None):
        return {"code": "99999", "msg": "Not implemented"}
    def perp_limit(self, symbol, side, price, size, tp=None, sl=None):
        return {"code": "99999", "msg": "Not implemented"}
    def get_positions(self, symbol=None):
        return []
    def close_position(self, symbol, hold_side):
        return {"code": "99999", "msg": "Not implemented"}
    def set_leverage(self, symbol, leverage, hold_side):
        return {"code": "99999", "msg": "Not implemented"}
    def set_margin_mode(self, symbol, mode):
        return {"code": "99999", "msg": "Not implemented"}
    @staticmethod
    def fetch_historical(symbol, granularity, days=7):
        return None
