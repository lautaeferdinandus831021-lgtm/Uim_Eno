import json, time, logging, threading, random
from datetime import datetime
from domain.trading.services import TradingService
from shared.utils.helpers import SimData

logger = logging.getLogger("bgbot.consumer")


class BotConsumer:
    def __init__(self, user_id, db_factory, redis):
        self.user_id = user_id
        self.db_factory = db_factory
        self.redis = redis
        self.running = False
        self.client = None
        self.thread = None
        self.config = self._load_config()
        self.api_cfg = self._load_api()
        self.trading = TradingService(self.config)
        self.state = {"running": False, "mode": self.config.get("market_mode", "spot"), "symbol": self.config.get("symbol", "BTCUSDT"), "balance": 0, "connected": False, "m1": {"signal": "NEUTRAL", "price": 0}, "m5": {"signal": "NEUTRAL", "price": 0}, "aligned": False, "positions": [], "risk_status": {}, "stats": {"total": 0, "wins": 0, "losses": 0, "total_pnl": 0}, "trades": [], "logs": []}
        self.prev_m5 = "NEUTRAL"
        self.last_trade_time = 0

    def _load_config(self):
        from sqlalchemy import text
        db = self.db_factory()
        try:
            r = db.execute(text("SELECT config_json FROM bot_configs WHERE user_id = :uid"), {"uid": self.user_id}).fetchone()
            if r and r[0]:
                cfg = r[0]
                if isinstance(cfg, str): cfg = json.loads(cfg)
                return cfg
        finally: db.close()
        from worker.app.config import worker_settings
        return worker_settings.DEFAULT_BOT_CONFIG.copy()

    def _load_api(self):
        from sqlalchemy import text
        from shared.utils.encryption import decrypt
        db = self.db_factory()
        try:
            r = db.execute(text("SELECT api_key, api_secret, api_passphrase, demo FROM api_configs WHERE user_id = :uid"), {"uid": self.user_id}).fetchone()
            if r: return {"api_key": decrypt(r[0] or ""), "api_secret": decrypt(r[1] or ""), "api_passphrase": decrypt(r[2] or ""), "demo": bool(r[3])}
        finally: db.close()
        return {}

    def _emit(self, event_type, data):
        try: self.redis.publish(f"user:{self.user_id}:events", json.dumps({"event": event_type, "data": data}))
        except Exception: pass

    def _log(self, level, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = {"time": ts, "level": level, "msg": msg}
        self.state["logs"].append(entry)
        if len(self.state["logs"]) > 500: self.state["logs"] = self.state["logs"][-500:]
        self._emit("log", entry)
        logger.info(f"[U{self.user_id}] {msg}")

    def _init_client(self):
        ac = self.api_cfg
        if not ac.get("api_key"):
            self._log("warn", "No API - SIM mode")
            return False
        try:
            from gateway import get_exchange
            self.client = get_exchange("bitget", ac["api_key"], ac["api_secret"], ac["api_passphrase"], ac.get("demo", True))
            result = self.client.test()
            if result["ok"]:
                self.state["connected"] = True
                self.state["balance"] = result["balance"]
                self._log("success", f"Connected! ${result['balance']:.2f}")
                return True
            self._log("error", f"API failed: {result.get('msg')}")
            return False
        except Exception as e:
            self._log("error", f"Connect: {e}")
            return False

    def _get_klines(self, symbol, gran, market):
        if self.state["connected"] and self.client:
            df = self.client.get_klines(symbol, gran, market)
            if df is not None and len(df) > 10: return df
        return SimData.gen(symbol, 200, {"1m": 1, "5m": 5}.get(gran, 1))

    def _loop(self):
        self._log("info", "=== Bot Engine Started ===")
        symbol = self.config.get("symbol", "BTCUSDT")
        mode = self.config.get("market_mode", "spot")
        interval = self.config.get("cooldown_seconds", 60)
        self._init_client()
        while self.running:
            try:
                msg = self.redis.get(f"user:{self.user_id}:stop")
                if msg: self.running = False; break
                df_m1 = self._get_klines(symbol, "1m", mode)
                df_m5 = self._get_klines(symbol, "5m", mode)
                if df_m1 is None or df_m5 is None: time.sleep(10); continue
                analysis = self.trading.analyze(df_m1, df_m5)
                m1, m5 = analysis["m1"], analysis["m5"]
                self.state.update({"m1": {"signal": m1["signal"], "price": m1["price"]}, "m5": {"signal": m5["signal"], "price": m5["price"]}, "aligned": analysis["aligned"]})
                self._log("tf", f"M1={m1['signal']} ${m1['price']:,.2f} | M5={m5['signal']} ${m5['price']:,.2f} {'ALIGNED' if analysis['aligned'] else ''}")
                now = time.time()
                cooldown_active = now - self.last_trade_time < interval
                order = self.trading.decide(m1["signal"], m5["signal"], self.prev_m5, self.state.get("balance", 0), cooldown_active, self.user_id)
                if order:
                    order.price = m5["price"]
                    tp, sl = self.trading.strategy.calculate_tp_sl(order.price, m5["signal"])
                    order.tp_price = tp
                    order.sl_price = sl
                    self._execute(order)
                    self.last_trade_time = now
                self.prev_m5 = m5["signal"]
                self.state["risk_status"] = self.trading.risk.get_status(self.state.get("balance", 0))
                self._emit("state_update", self.state)
                if m1.get("overlays"): self._emit("chart_m1", {"candles": self._to_candles(df_m1), "overlays": m1["overlays"], "signals": {"macd": m1["signal"]}, "price": m1["price"]})
                if m5.get("overlays"): self._emit("chart_m5", {"candles": self._to_candles(df_m5), "overlays": m5["overlays"], "signals": {"macd": m5["signal"]}, "price": m5["price"]})
                for _ in range(interval):
                    if not self.running: break
                    time.sleep(1)
            except Exception as e:
                self._log("error", f"Loop: {e}")
                time.sleep(10)
        self._log("warn", "Bot stopped")
        self.state["running"] = False
        self._emit("state_update", self.state)

    def _execute(self, order):
        if not self.state["connected"]:
            pnl = round(random.uniform(-5, 12), 2)
            self.trading.record_result(pnl, self.user_id)
            self.state["stats"]["total"] += 1
            self.state["stats"]["total_pnl"] = round(self.state["stats"]["total_pnl"] + pnl, 2)
            if pnl >= 0: self.state["stats"]["wins"] += 1
            else: self.state["stats"]["losses"] += 1
            trade = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "mode": order.mode, "side": order.side, "pair": order.symbol, "price": order.price, "pnl": pnl, "status": "simulated"}
            self.state["trades"] = [trade] + self.state.get("trades", [])[:100]
            self._emit("trade", trade)
            from sqlalchemy import text
            db = self.db_factory()
            try:
                db.execute(text("INSERT INTO trades (user_id, mode, side, pair, price, size, pnl, status) VALUES (:u,:m,:s,:p,:pr,:sz,:pn,:st)"), {"u": self.user_id, "m": order.mode, "s": order.side, "p": order.symbol, "pr": order.price, "sz": order.size, "pn": pnl, "st": "simulated"})
                db.commit()
            finally: db.close()
            self._log("trade", f"[SIM] {order.side.upper()} {order.symbol} @ ${order.price:,.2f} PnL: ${pnl:+.2f}")

    def _to_candles(self, df):
        return [{"time": int(r["timestamp"].timestamp()), "open": float(r["open"]), "high": float(r["high"]), "low": float(r["low"]), "close": float(r["close"])} for _, r in df.iterrows()]

    def update_positions(self):
        if self.state["connected"] and self.client:
            try: self.state["positions"] = self.client.get_positions()
            except Exception: pass

    def start(self):
        if self.running: return
        self.running = True
        self.state["running"] = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.state["running"] = False
