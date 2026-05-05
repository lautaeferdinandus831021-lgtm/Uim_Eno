"""
Bitget API v2 Client - Spot + Perpetual (Futures)
Supports: Market, Limit, Stop-Limit orders
"""
import time, hmac, hashlib, base64, json, httpx, logging

logger = logging.getLogger("bgbot.bitget")

BITGET_BASE = "https://api.bitget.com"
TOR_PROXY = "socks5://127.0.0.1:9050"


def sign(timestamp, method, path, body="", secret=""):
    message = timestamp + method.upper() + path + body
    mac = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("utf-8")


class BitgetClient:
    def __init__(self, api_key="", api_secret="", passphrase=""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.base_url = BITGET_BASE
        self.timeout = 20

    @property
    def is_configured(self):
        return bool(self.api_key and self.api_secret)

    def _headers(self, method, path, body=""):
        ts = str(int(time.time() * 1000))
        sig = sign(ts, method, path, body, self.api_secret)
        return {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": sig,
            "ACCESS-TIMESTAMP": ts,
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
            "locale": "en-US",
        }

    async def _request(self, method, path, params=None, body=None):
        url = self.base_url + path
        body_str = json.dumps(body) if body else ""

        headers = {}
        if self.is_configured:
            query = ""
            if params:
                query = "?" + "&".join(f"{k}={v}" for k, v in params.items())
            headers = self._headers(method, path + query, body_str)

        try:
            for proxy in [None, TOR_PROXY]:
                try:
                    async with httpx.AsyncClient(timeout=self.timeout, verify=False, proxy=proxy) as client:
                        if method == "GET":
                            resp = await client.get(url, params=params, headers=headers)
                        else:
                            resp = await client.post(url, content=body_str, headers=headers)

                    try:
                        data = resp.json()
                        if isinstance(data, dict) and data.get("code") is not None:
                            return data
                    except Exception:
                        pass

                    if "html" in resp.text.lower()[:100]:
                        logger.info("Blocked direct, trying Tor proxy...")
                        continue

                    try:
                        return resp.json()
                    except Exception:
                        return {"code": "error", "msg": f"Invalid response: {resp.text[:100]}"}

                except Exception as e:
                    if proxy is None:
                        logger.info(f"Direct failed ({e}), trying Tor...")
                        continue
                    else:
                        raise

            return {"code": "error", "msg": "All connection methods failed"}
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"code": "error", "msg": str(e)[:200]}

    # ==================== PUBLIC ====================
    async def get_ticker(self, symbol="BTCUSDT"):
        data = await self._request("GET", "/api/v2/spot/market/tickers", {"symbol": symbol})
        if data.get("code") == "00000" and data.get("data"):
            t = data["data"][0]
            return {
                "symbol": symbol,
                "price": float(t.get("lastPr", 0)),
                "change24h": float(t.get("change24h", 0)),
                "high24h": float(t.get("high24h", 0)),
                "low24h": float(t.get("low24h", 0)),
                "volume24h": float(t.get("baseVolume", 0)),
            }
        return {"symbol": symbol, "price": 0, "error": data.get("msg", "unavailable")}

    async def get_futures_ticker(self, symbol="BTCUSDT"):
        data = await self._request("GET", "/api/v2/mix/market/ticker", {"symbol": symbol, "productType": "USDT-FUTURES"})
        if data.get("code") == "00000" and data.get("data"):
            t = data["data"]
            if isinstance(t, list):
                t = t[0] if t else {}
            if not isinstance(t, dict):
                return {"symbol": symbol, "price": 0, "error": "Unexpected data format"}
            return {
                "symbol": symbol,
                "price": float(t.get("lastPr", 0) or 0),
                "change24h": float(t.get("change24h", 0) or 0),
                "high24h": float(t.get("high24h", 0) or 0),
                "low24h": float(t.get("low24h", 0) or 0),
                "volume24h": float(t.get("baseVolume", 0) or 0),
                "fundingRate": float(t.get("fundingRate", 0) or 0),
                "nextFundingTime": str(t.get("nextFundingTime", "")),
                "openInterest": float(t.get("openInterest", 0) or 0),
            }
        return {"symbol": symbol, "price": 0, "error": data.get("msg", "unavailable")}

    async def get_klines(self, symbol="BTCUSDT", granularity="1min", limit=200):
        """Get candlestick data. Returns list of {time, open, high, low, close, volume}"""
        data = await self._request("GET", "/api/v2/spot/market/candles", {
            "symbol": symbol,
            "granularity": granularity,
            "limit": str(limit),
        })
        if data.get("code") == "00000":
            candles = []
            raw = data.get("data", [])
            for c in raw:
                try:
                    if isinstance(c, list) and len(c) >= 6:
                        candles.append({
                            "time": int(c[0]),
                            "open": float(c[1]),
                            "high": float(c[2]),
                            "low": float(c[3]),
                            "close": float(c[4]),
                            "volume": float(c[5]),
                        })
                    elif isinstance(c, dict):
                        candles.append({
                            "time": int(c.get("ts", 0)),
                            "open": float(c.get("open", 0)),
                            "high": float(c.get("high", 0)),
                            "low": float(c.get("low", 0)),
                            "close": float(c.get("close", 0)),
                            "volume": float(c.get("baseVol", 0)),
                        })
                except (ValueError, TypeError, IndexError):
                    continue
            candles.sort(key=lambda x: x["time"])
            return candles
        return []
    async def get_futures_klines(self, symbol="BTCUSDT", granularity="5min", limit=200):
        gran_map = {"1min": "1min", "5min": "5min", "15min": "15min", "1h": "1H", "4h": "4H", "1d": "1Dutc"}
        gran = gran_map.get(granularity, "5min")
        data = await self._request("GET", "/api/v2/mix/market/candles", {
            "symbol": symbol, "granularity": gran, "limit": str(limit), "productType": "USDT-FUTURES",
        })
        if data.get("code") == "00000":
            candles = []
            for row in data.get("data", []):
                try:
                    candles.append({
                        "timestamp": int(row[0]), "open": float(row[1]),
                        "high": float(row[2]), "low": float(row[3]),
                        "close": float(row[4]), "volume": float(row[5]),
                    })
                except (IndexError, ValueError):
                    continue
            candles.reverse()
            return candles
        return []

    async def get_orderbook(self, symbol="BTCUSDT", limit=20):
        data = await self._request("GET", "/api/v2/spot/market/orderbook", {
            "symbol": symbol, "limit": str(limit),
        })
        if data.get("code") == "00000":
            book = data.get("data", {})
            bids = [[float(p), float(q)] for p, q in book.get("bids", []) if p and q]
            asks = [[float(p), float(q)] for p, q in book.get("asks", []) if p and q]
            return {"bids": bids, "asks": asks}
        return {"bids": [], "asks": [], "error": data.get("msg")}

    # ==================== SPOT ACCOUNT ====================
    async def get_spot_account(self):
        if not self.is_configured:
            return {"error": "API not configured", "assets": []}
        data = await self._request("GET", "/api/v2/spot/account/assets")
        if data.get("code") == "00000":
            assets = []
            for a in data.get("data", []):
                avail = float(a.get("available", 0))
                frozen = float(a.get("frozen", 0))
                if avail > 0 or frozen > 0:
                    assets.append({
                        "coin": a.get("coin", ""),
                        "available": avail,
                        "frozen": frozen,
                        "total": avail + frozen,
                        "usdt_value": float(a.get("usdtValue", 0) or 0),
                    })
            return {"assets": assets, "total_usdt": sum(a["usdt_value"] for a in assets)}
        return {"error": data.get("msg", "Auth failed"), "assets": []}

    # ==================== FUTURES ACCOUNT ====================
    async def get_futures_account(self, symbol="BTCUSDT"):
        if not self.is_configured:
            return {"error": "API not configured", "assets": []}
        data = await self._request("GET", "/api/v2/mix/account/accounts", {
            "productType": "USDT-FUTURES",
        })
        if data.get("code") == "00000":
            assets = []
            for a in data.get("data", []):
                avail = float(a.get("available", 0))
                frozen = float(a.get("frozen", 0))
                if avail > 0 or frozen > 0:
                    assets.append({
                        "coin": a.get("marginCoin", ""),
                        "available": avail,
                        "frozen": frozen,
                        "total": avail + frozen,
                        "usdt_equity": float(a.get("usdtEquity", 0) or 0),
                    })
            return {"assets": assets, "total_usdt": sum(a.get("usdt_equity", 0) for a in assets)}
        return {"error": data.get("msg", "Auth failed"), "assets": []}

    async def get_futures_positions(self, symbol="BTCUSDT"):
        if not self.is_configured:
            return {"error": "API not configured", "positions": []}
        data = await self._request("GET", "/api/v2/mix/position/all-position", {
            "productType": "USDT-FUTURES",
        })
        if data.get("code") == "00000":
            positions = []
            items = data.get("data", [])
            if isinstance(items, dict):
                items = items.get("list", []) if "list" in items else [items]
            for p in items:
                if isinstance(p, str):
                    continue
                if isinstance(p, dict):
                    size = float(p.get("total", 0) or 0)
                    if size > 0 and str(p.get("symbol", "")).upper() == symbol.upper():
                        positions.append({
                            "symbol": str(p.get("symbol", "")),
                            "side": str(p.get("holdSide", "")),
                            "size": size,
                            "avg_price": float(p.get("averageOpenPrice", 0) or 0),
                            "mark_price": float(p.get("markPrice", 0) or 0),
                            "unrealized_pnl": float(p.get("unrealizedPL", 0) or 0),
                            "leverage": int(p.get("leverage", 1) or 1),
                            "margin": float(p.get("marginSize", 0) or 0),
                            "margin_mode": str(p.get("marginMode", "cross")),
                        })
            return {"positions": positions}
        return {"error": data.get("msg", "unknown"), "positions": []}

    # ==================== SPOT ORDERS ====================
    async def spot_market_buy(self, symbol, quote_size):
        """Market buy by USDT amount"""
        if not self.is_configured:
            return {"error": "API not configured"}
        body = {
            "symbol": symbol,
            "side": "buy",
            "orderType": "market",
            "size": str(quote_size),
        }
        data = await self._request("POST", "/api/v2/spot/trade/place-order", body=body)
        if data.get("code") == "00000":
            return {"ok": True, "order_id": data.get("data", {}).get("orderId", "")}
        return {"error": data.get("msg", "Order failed")}

    async def spot_market_sell(self, symbol, base_size):
        """Market sell by coin amount"""
        if not self.is_configured:
            return {"error": "API not configured"}
        body = {
            "symbol": symbol,
            "side": "sell",
            "orderType": "market",
            "size": str(base_size),
        }
        data = await self._request("POST", "/api/v2/spot/trade/place-order", body=body)
        if data.get("code") == "00000":
            return {"ok": True, "order_id": data.get("data", {}).get("orderId", "")}
        return {"error": data.get("msg", "Order failed")}

    async def spot_limit_buy(self, symbol, size, price):
        """Limit buy order"""
        if not self.is_configured:
            return {"error": "API not configured"}
        body = {
            "symbol": symbol,
            "side": "buy",
            "orderType": "limit",
            "size": str(size),
            "price": str(price),
        }
        data = await self._request("POST", "/api/v2/spot/trade/place-order", body=body)
        if data.get("code") == "00000":
            return {"ok": True, "order_id": data.get("data", {}).get("orderId", "")}
        return {"error": data.get("msg", "Order failed")}

    async def spot_limit_sell(self, symbol, size, price):
        """Limit sell order"""
        if not self.is_configured:
            return {"error": "API not configured"}
        body = {
            "symbol": symbol,
            "side": "sell",
            "orderType": "limit",
            "size": str(size),
            "price": str(price),
        }
        data = await self._request("POST", "/api/v2/spot/trade/place-order", body=body)
        if data.get("code") == "00000":
            return {"ok": True, "order_id": data.get("data", {}).get("orderId", "")}
        return {"error": data.get("msg", "Order failed")}

    async def spot_stop_limit(self, symbol, side, size, price, trigger_price):
        """Stop-Limit order (trigger then limit)"""
        if not self.is_configured:
            return {"error": "API not configured"}
        body = {
            "symbol": symbol,
            "side": side,
            "orderType": "limit",
            "size": str(size),
            "price": str(price),
            "triggerPrice": str(trigger_price),
        }
        data = await self._request("POST", "/api/v2/spot/trade/place-order", body=body)
        if data.get("code") == "00000":
            return {"ok": True, "order_id": data.get("data", {}).get("orderId", "")}
        return {"error": data.get("msg", "Order failed")}

    async def spot_cancel_order(self, symbol, order_id):
        """Cancel spot order"""
        if not self.is_configured:
            return {"error": "API not configured"}
        body = {"symbol": symbol, "orderId": str(order_id)}
        data = await self._request("POST", "/api/v2/spot/trade/cancel-order", body=body)
        if data.get("code") == "00000":
            return {"ok": True, "msg": "Order cancelled"}
        return {"error": data.get("msg", "Cancel failed")}

    async def get_spot_orders(self, symbol="BTCUSDT"):
        """Get open spot orders"""
        if not self.is_configured:
            return {"error": "API not configured", "orders": []}
        data = await self._request("GET", "/api/v2/spot/trade/unfilled-orders", {
            "symbol": symbol, "limit": "50",
        })
        if data.get("code") == "00000":
            orders = []
            for o in data.get("data", []):
                if isinstance(o, str):
                    continue
                if isinstance(o, dict):
                    orders.append({
                        "order_id": str(o.get("orderId", "")),
                        "symbol": str(o.get("symbol", "")),
                        "side": str(o.get("side", "")),
                        "order_type": str(o.get("orderType", "")),
                        "price": float(o.get("price", 0) or 0),
                        "size": float(o.get("size", 0) or 0),
                        "filled": float(o.get("filledQty", 0) or 0),
                        "status": str(o.get("status", "")),
                        "create_time": str(o.get("cTime", "")),
                    })
            return {"orders": orders}
        return {"error": data.get("msg", "unknown"), "orders": []}

    async def get_spot_history(self, symbol="BTCUSDT", limit=20):
        """Get spot trade history"""
        if not self.is_configured:
            return {"error": "API not configured", "trades": []}
        data = await self._request("GET", "/api/v2/spot/trade/fills", {
            "symbol": symbol, "limit": str(limit),
        })
        if data.get("code") == "00000":
            trades = []
            for t in data.get("data", []):
                if isinstance(t, str):
                    continue
                if isinstance(t, dict):
                    trades.append({
                        "trade_id": str(t.get("tradeId", "")),
                        "order_id": str(t.get("orderId", "")),
                        "symbol": str(t.get("symbol", "")),
                        "side": str(t.get("side", "")),
                        "price": float(t.get("priceAvg", 0) or 0),
                        "size": float(t.get("size", 0) or 0),
                        "fee": float(t.get("fee", 0) or 0),
                        "time": str(t.get("cTime", "")),
                    })
            return {"trades": trades}
        return {"error": data.get("msg", "unknown"), "trades": []}

    # ==================== FUTURES ORDERS ====================
    async def futures_set_leverage(self, symbol, leverage, margin_mode="crossed"):
        """Set leverage for futures"""
        if not self.is_configured:
            return {"error": "API not configured"}
        body = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",
            "leverage": str(leverage),
            "marginMode": margin_mode,
        }
        data = await self._request("POST", "/api/v2/mix/account/set-leverage", body=body)
        if data.get("code") == "00000":
            return {"ok": True, "leverage": leverage}
        return {"error": data.get("msg", "Set leverage failed")}

    async def futures_market_open(self, symbol, side, size, leverage=10, margin_mode="crossed"):
        """Open futures position with market order
        side: long or short
        size: in lots (for BTCUSDT, 1 lot = 0.001 BTC, min = 10 lots = 0.01 BTC)
        """
        if size < 10:
            size = 10  # Minimum 0.01 BTC
        if not self.is_configured:
            return {"error": "API not configured"}

        # Set leverage first
        await self.futures_set_leverage(symbol, leverage, margin_mode)

        body = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",
            "marginMode": margin_mode,
            "marginCoin": "USDT",
            "size": str(size),
            "side": side,  # open_long or open_short
            "orderType": "market",
        }
        data = await self._request("POST", "/api/v2/mix/order/place-order", body=body)
        if data.get("code") == "00000":
            return {"ok": True, "order_id": data.get("data", {}).get("orderId", "")}
        return {"error": data.get("msg", "Order failed")}

    async def futures_market_close(self, symbol, side, size, leverage=10, margin_mode="crossed"):
        """Close futures position with market order
        side: long or short (the position side to close)
        """
        if not self.is_configured:
            return {"error": "API not configured"}

        close_side = "close_long" if side == "long" else "close_short"
        body = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",
            "marginMode": margin_mode,
            "marginCoin": "USDT",
            "size": str(size),
            "side": close_side,
            "orderType": "market",
        }
        data = await self._request("POST", "/api/v2/mix/order/place-order", body=body)
        if data.get("code") == "00000":
            return {"ok": True, "order_id": data.get("data", {}).get("orderId", "")}
        return {"error": data.get("msg", "Close failed")}

    async def futures_limit_open(self, symbol, side, size, price, leverage=10, margin_mode="crossed"):
        """Open futures position with limit order (min 10 lots = 0.01 BTC)"""
        if not self.is_configured:
            return {"error": "API not configured"}
        if size < 10:
            size = 10

        await self.futures_set_leverage(symbol, leverage, margin_mode)

        body = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",
            "marginMode": margin_mode,
            "marginCoin": "USDT",
            "size": str(size),
            "side": side,  # open_long or open_short
            "orderType": "limit",
            "price": str(price),
        }
        data = await self._request("POST", "/api/v2/mix/order/place-order", body=body)
        if data.get("code") == "00000":
            return {"ok": True, "order_id": data.get("data", {}).get("orderId", "")}
        return {"error": data.get("msg", "Order failed")}

    async def futures_stop_tp_sl(self, symbol, side, size, tp_price=None, sl_price=None, plan_type="pos_loss"):
        """Set TP/SL for futures position"""
        if not self.is_configured:
            return {"error": "API not configured"}

        results = []

        if tp_price:
            body = {
                "symbol": symbol,
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "planType": "pos_profit",
                "triggerPrice": str(tp_price),
                "holdSide": side,
                "size": str(size),
            }
            data = await self._request("POST", "/api/v2/mix/order/place-plan-order", body=body)
            results.append({"tp": tp_price, "ok": data.get("code") == "00000", "error": data.get("msg", "")})

        if sl_price:
            body = {
                "symbol": symbol,
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "planType": "pos_loss",
                "triggerPrice": str(sl_price),
                "holdSide": side,
                "size": str(size),
            }
            data = await self._request("POST", "/api/v2/mix/order/place-plan-order", body=body)
            results.append({"sl": sl_price, "ok": data.get("code") == "00000", "error": data.get("msg", "")})

        return {"results": results}

    async def futures_cancel_order(self, symbol, order_id):
        """Cancel futures order"""
        if not self.is_configured:
            return {"error": "API not configured"}
        body = {"symbol": symbol, "orderId": str(order_id), "productType": "USDT-FUTURES"}
        data = await self._request("POST", "/api/v2/mix/order/cancel-order", body=body)
        if data.get("code") == "00000":
            return {"ok": True, "msg": "Order cancelled"}
        return {"error": data.get("msg", "Cancel failed")}

    async def get_futures_orders(self, symbol="BTCUSDT"):
        """Get open futures orders"""
        if not self.is_configured:
            return {"error": "API not configured", "orders": []}
        data = await self._request("GET", "/api/v2/mix/order/orders-pending", {
            "symbol": symbol, "productType": "USDT-FUTURES",
        })
        if data.get("code") == "00000":
            orders = []
            for o in data.get("data", []):
                if isinstance(o, str):
                    continue
                if isinstance(o, dict):
                    orders.append({
                        "order_id": str(o.get("orderId", "")),
                        "symbol": str(o.get("symbol", "")),
                        "side": str(o.get("side", "")),
                        "order_type": str(o.get("orderType", "")),
                        "price": float(o.get("price", 0) or 0),
                        "size": float(o.get("size", 0) or 0),
                        "filled": float(o.get("filledQty", 0) or 0),
                        "status": str(o.get("status", "")),
                        "leverage": str(o.get("leverage", "")),
                        "create_time": str(o.get("cTime", "")),
                    })
            return {"orders": orders}
        return {"error": data.get("msg", "unknown"), "orders": []}

    async def get_futures_history(self, symbol="BTCUSDT", limit=20):
        """Get futures trade history"""
        if not self.is_configured:
            return {"error": "API not configured", "trades": []}
        data = await self._request("GET", "/api/v2/mix/order/fills-history", {
            "symbol": symbol, "productType": "USDT-FUTURES", "limit": str(limit),
        })
        if data.get("code") == "00000":
            trades = []
            for t in data.get("data", []):
                if isinstance(t, str):
                    continue
                if isinstance(t, dict):
                    trades.append({
                        "trade_id": str(t.get("tradeId", "")),
                        "order_id": str(t.get("orderId", "")),
                        "symbol": str(t.get("symbol", "")),
                        "side": str(t.get("side", "")),
                        "price": float(t.get("priceAvg", 0) or 0),
                        "size": float(t.get("size", 0) or 0),
                        "fee": float(t.get("fee", 0) or 0),
                        "pnl": float(t.get("pnl", 0) or 0),
                        "time": str(t.get("cTime", "")),
                    })
            return {"trades": trades}
        return {"error": data.get("msg", "unknown"), "trades": []}

    # ==================== LEGACY ====================
    async def get_account(self):
        return await self.get_spot_account()

    async def get_balance(self):
        account = await self.get_spot_account()
        if "error" in account:
            return 0
        return account.get("total_usdt", 0)

    async def place_order(self, symbol, side, size, order_type="market", price=None):
        if side == "buy":
            if order_type == "market":
                return await self.spot_market_buy(symbol, size)
            elif order_type == "limit" and price:
                return await self.spot_limit_buy(symbol, size, price)
        elif side == "sell":
            if order_type == "market":
                return await self.spot_market_sell(symbol, size)
            elif order_type == "limit" and price:
                return await self.spot_limit_sell(symbol, size, price)
        return {"error": "Invalid order parameters"}

    async def get_orders(self, symbol="BTCUSDT", limit=20):
        return await self.get_spot_orders(symbol)
