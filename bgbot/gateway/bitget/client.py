import json, time, hmac, hashlib, base64, logging
import requests as http_requests
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from gateway.base import ExchangeGateway

logger = logging.getLogger("bgbot.bitget")


class BitgetClient(ExchangeGateway):
    BASE = "https://api.bitget.com"

    def __init__(self, key, secret, passphrase, demo=True):
        self.key, self.secret, self.passphrase, self.demo = key, secret, passphrase, demo
        self.sess = http_requests.Session()
        self.last_req = 0.0

    def _rl(self):
        dt = time.time() - self.last_req
        if dt < 0.2:
            time.sleep(0.2 - dt)
        self.last_req = time.time()

    def _sign(self, ts, method, path, body=""):
        return base64.b64encode(hmac.new(self.secret.encode(), (ts + method.upper() + path + body).encode(), hashlib.sha256).digest()).decode()

    def _hdr(self, method, path, body=""):
        ts = str(int(time.time()))
        h = {"ACCESS-KEY": self.key, "ACCESS-SIGN": self._sign(ts, method, path, body), "ACCESS-TIMESTAMP": ts, "ACCESS-PASSPHRASE": self.passphrase, "Content-Type": "application/json", "locale": "en-US"}
        if self.demo:
            h["paptrading"] = "1"
        return h

    def _req(self, method, path, params=None, data=None):
        self._rl()
        body = json.dumps(data) if data else ""
        for i in range(3):
            try:
                r = self.sess.request(method, self.BASE + path, headers=self._hdr(method, path, body), params=params, data=body or None, timeout=15)
                return r.json()
            except Exception as e:
                if i < 2:
                    time.sleep(1 * (i + 1))
                else:
                    return {"code": "99999", "msg": str(e)}

    def test(self):
        try:
            return {"ok": True, "balance": self.get_balance("spot")}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def get_balance(self, market="spot"):
        try:
            if market == "spot":
                r = self._req("GET", "/api/v2/spot/account/assets", {"coin": "USDT"})
                if r and r.get("data") and r["data"]:
                    return float(r["data"][0].get("available", 0))
            else:
                r = self._req("GET", "/api/v2/account/get-account-balance", {"productType": "USDT-FUTURES"})
                if r and r.get("data"):
                    return float(r["data"][0].get("available", 0))
        except Exception:
            pass
        return 0

    def get_klines(self, symbol, granularity, market="spot", limit=200):
        path = "/api/v2/spot/market/candles" if market == "spot" else "/api/v2/mix/market/candles"
        params = {"symbol": symbol, "granularity": granularity, "limit": str(limit)}
        if market != "spot":
            params["productType"] = "USDT-FUTURES"
        result = self._req("GET", path, params)
        if not result or result.get("code") != "00000":
            return None
        try:
            df = pd.DataFrame(result["data"], columns=["timestamp", "open", "high", "low", "close", "volume", "quote_volume"])
            for c in ["open", "high", "low", "close", "volume"]:
                df[c] = pd.to_numeric(df[c])
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
            return df.sort_values("timestamp").reset_index(drop=True)
        except Exception:
            return None

    def spot_market(self, symbol, side, size):
        return self._req("POST", "/api/v2/spot/trade/place-order", data={"symbol": symbol, "side": side, "orderType": "market", "force": "gtc", "size": str(size)})

    def spot_limit(self, symbol, side, price, size):
        return self._req("POST", "/api/v2/spot/trade/place-order", data={"symbol": symbol, "side": side, "orderType": "limit", "force": "gtc", "price": str(price), "size": str(size)})

    def perp_market(self, symbol, side, size, tp=None, sl=None):
        d = {"productType": "USDT-FUTURES", "symbol": symbol, "marginMode": "crossed", "marginCoin": "USDT", "size": str(size), "side": side, "orderType": "market"}
        if tp: d["presetStopSurplusPrice"] = str(tp)
        if sl: d["presetStopLossPrice"] = str(sl)
        return self._req("POST", "/api/v2/mix/order/place-order", data=d)

    def perp_limit(self, symbol, side, price, size, tp=None, sl=None):
        d = {"productType": "USDT-FUTURES", "symbol": symbol, "marginMode": "crossed", "marginCoin": "USDT", "size": str(size), "side": side, "orderType": "limit", "price": str(price)}
        if tp: d["presetStopSurplusPrice"] = str(tp)
        if sl: d["presetStopLossPrice"] = str(sl)
        return self._req("POST", "/api/v2/mix/order/place-order", data=d)

    def get_positions(self, symbol=None):
        params = {"productType": "USDT-FUTURES"}
        if symbol: params["symbol"] = symbol
        r = self._req("GET", "/api/v2/mix/position/get-all-position", params)
        if r and r.get("data"):
            return [p for p in r["data"] if float(p.get("total", 0)) > 0]
        return []

    def close_position(self, symbol, hold_side):
        return self._req("POST", "/api/v2/mix/order/close-positions", data={"productType": "USDT-FUTURES", "symbol": symbol, "holdSide": hold_side})

    def set_leverage(self, symbol, leverage, hold_side):
        return self._req("POST", "/api/v2/mix/account/set-leverage", data={"productType": "USDT-FUTURES", "symbol": symbol, "leverage": str(leverage), "holdSide": hold_side})

    def set_margin_mode(self, symbol, mode):
        return self._req("POST", "/api/v2/mix/account/set-margin-mode", data={"productType": "USDT-FUTURES", "symbol": symbol, "marginMode": mode, "marginCoin": "USDT"})

    @staticmethod
    def fetch_historical(symbol, granularity, days=7):
        all_data = []
        end_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        ms_map = {"1m": 60000, "5m": 300000, "15m": 900000, "1h": 3600000, "4h": 14400000, "1d": 86400000}
        ms = ms_map.get(granularity, 60000)
        total = int((days * 86400000) / ms)
        fetched = 0
        while fetched < total:
            try:
                r = http_requests.get("https://api.bitget.com/api/v2/spot/market/candles", params={"symbol": symbol, "granularity": granularity, "limit": "200", "endTime": str(end_ts)}, timeout=10)
                data = r.json()
                if data.get("code") != "00000" or not data.get("data"):
                    break
                rows = data["data"]
                if not rows: break
                all_data.extend(rows)
                end_ts = int(rows[-1][0]) - 1
                fetched += len(rows)
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"Historical: {e}")
                break
        if not all_data: return None
        df = pd.DataFrame(all_data, columns=["timestamp", "open", "high", "low", "close", "volume", "quote_volume"])
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c])
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
        return df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
