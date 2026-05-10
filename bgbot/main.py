from ws_macd_engine import BitgetWebSocket
import os, sys, hashlib, secrets, logging, time, traceback, json
from datetime import datetime, timedelta, timezone
from typing import Optional

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, select, func
from jose import jwt, JWTError
from bitget_client import BitgetClient
from trade_engine import calc_macd_series, analyze_m1_m5, should_trade, calc_tp_sl, RealTimeMACD
from perpetual_engine import start_perp_bot, stop_perp_bot, get_perp_status, perp_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bgbot")

DB_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./bgbot_v3.db")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-jwt-secret-12345678")
JWT_ALG = "HS256"

engine = create_async_engine(DB_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass


# ===== MODELS =====
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(500), default="")
    provider: Mapped[str] = mapped_column(String(50), default="email")
    last_login: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    trade_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    mode: Mapped[str] = mapped_column(String(20), default="spot")
    side: Mapped[str] = mapped_column(String(10), default="buy")
    pair: Mapped[str] = mapped_column(String(20), default="BTCUSDT")
    price: Mapped[float] = mapped_column(Float, default=0)
    size: Mapped[float] = mapped_column(Float, default=0)
    pnl: Mapped[float] = mapped_column(Float, default=0)
    pnl_pct: Mapped[float] = mapped_column(Float, default=0)
    fee: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(20), default="simulated")
    order_id: Mapped[str] = mapped_column(String(100), default="")

class BotConfig(Base):
    __tablename__ = "bot_configs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ApiConfig(Base):
    __tablename__ = "api_configs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    api_key: Mapped[str] = mapped_column(String(500), default="")
    api_secret: Mapped[str] = mapped_column(String(500), default="")
    api_passphrase: Mapped[str] = mapped_column(String(500), default="")
    demo: Mapped[bool] = mapped_column(Boolean, default=True)

class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    trades_json: Mapped[str] = mapped_column(Text, default="[]")
    equity_json: Mapped[str] = mapped_column(Text, default="[]")


# ===== SECURITY =====
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${pw_hash}"

def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt, pw_hash = hashed.split("$", 1)
        return hashlib.sha256((salt + plain).encode()).hexdigest() == pw_hash
    except:
        return False

def create_token(uid: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    return jwt.encode({"uid": uid, "email": email, "exp": expire}, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        return None

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    if not credentials:
        raise HTTPException(401, "Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid token")
    result = await db.execute(select(User).where(User.id == payload["uid"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "User not found")
    return user


# ===== LIFESPAN =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("BG-BOT v5 started (SQLite)")
    await bws.start()
    bws._config_store = _config_store
    _bws_task = asyncio.create_task(_bws_updater())
    _atask = asyncio.create_task(run_analysis_loop())
    yield
    _atask.cancel()
    await engine.dispose()
    logger.info("BG-BOT v5 stopped")



import asyncio



# ===== DIRECT REST API (NO PROXY) =====
import httpx as _httpx_direct

async def get_klines_direct(symbol="BTCUSDT", granularity="1min", limit=200):
    """Fetch klines directly from Bitget (no proxy)"""
    url = f"https://api.bitget.com/api/v2/spot/market/candles"
    params = {"symbol": symbol, "granularity": granularity, "limit": str(limit)}
    try:
        async with _httpx_direct.AsyncClient(timeout=10, verify=False) as client:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                data = r.json().get("data", [])
                result = []
                for row in data:
                    # Bitget format: [timestamp, open, high, low, close, volume, turnover]
                    if len(row) >= 5:
                        result.append({
                            "timestamp": int(row[0]),
                            "open": float(row[1]),
                            "high": float(row[2]),
                            "low": float(row[3]),
                            "close": float(row[4]),
                            "volume": float(row[5]) if len(row) > 5 else 0,
                        })
                return result
    except Exception as e:
        logger.error(f"Direct klines error: {e}")
    return []

async def get_price_direct(symbol="BTCUSDT"):
    """Fetch current price directly from Bitget (no proxy)"""
    url = f"https://api.bitget.com/api/v2/spot/market/tickers"
    params = {"symbol": symbol}
    try:
        async with _httpx_direct.AsyncClient(timeout=10, verify=False) as client:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    return float(data[0].get("lastPr", 0))
    except Exception as e:
        logger.error(f"Direct price error: {e}")
    return 0.0

# ===== BOT STATE =====
import random as _rnd
bot_running = False
bot_trades_log = []

# Config storage
_config_store = {"api_key": "", "api_secret": "", "api_passphrase": "", "m1": {"fast": 4, "slow": 5, "signal": 3, "source": "close"}, "m5": {"fast": 4, "slow": 5, "signal": 3, "source": "close"}, "m1_bb_length": 6, "m1_bb_std": 1.2, "m1_rsi_length": 6, "m1_bb_enabled": True, "m1_macd_enabled": True, "m1_rsi_enabled": True, "m5_bb_length": 6, "m5_bb_std": 1.2, "m5_rsi_length": 6, "m5_bb_enabled": True, "m5_macd_enabled": True, "m5_rsi_enabled": True, "pair": "BTCUSDT", "order_size": 0.001, "tp_percent": 0.6, "sl_percent": 0.3, "mode": "spot", "balance_type": "demo"}
bot_initial_balance = 10000.0
bot_realized_pnl = 0.0

# ===== REAL-TIME STREAMING ENGINE =====
from trade_engine import RealTimeMACD

bws = BitgetWebSocket(m1_fast=4, m1_slow=5, m1_sig=3, m5_fast=4, m5_slow=5, m5_sig=3)

ws_price = 0.0
ws_connected = False
ws_last_tick = 0



bot_position = None
bot_analysis = {"m1": {}, "m5": {}, "aligned": False, "trade_signal": "NEUTRAL"}

# ===== ALWAYS-ON MARKET ANALYSIS =====
_bot_config_cache = {"m1": {"fast": 4, "slow": 5, "signal": 3}, "m5": {"fast": 4, "slow": 5, "signal": 3}}

async def run_analysis_loop():
    """Always analyze market, slower when bot is stopped"""
    global bot_analysis, _bot_config_cache
    await asyncio.sleep(3)
    logger.info("Analysis loop started (always-on)")
    while True:
        try:
            m1 = await get_klines_direct("BTCUSDT", "1min", 200)
            m5 = await get_klines_direct("BTCUSDT", "5min", 200)
            if m1 and m5:
                c1 = [x["close"] for x in m1]
                c5 = [x["close"] for x in m5]
                bot_analysis = analyze_m1_m5(c1, c5, _bot_config_cache)
        except Exception as e:
            logger.error(f"Analysis loop: {e}")
        await asyncio.sleep(10)

spot_macd_m1 = None
spot_macd_m5 = None

async def get_user_bitget(user_id, db):
    result = await db.execute(select(ApiConfig).where(ApiConfig.user_id == user_id))
    cfg = result.scalar_one_or_none()
    if cfg and cfg.api_key:
        return BitgetClient(cfg.api_key, cfg.api_secret, cfg.api_passphrase)
    return BitgetClient()  # Public only

async def run_bot_tick(user_id, db):
    global bot_trades_log, bot_position, bot_analysis, spot_macd_m1, spot_macd_m5
    pair = "BTCUSDT"
    client = await get_user_bitget(user_id, db)

    # Get real OHLC data - more candles for accurate MACD
    candles_m1 = await client.get_klines(pair, "1min", 200)
    candles_m5 = await client.get_klines(pair, "5min", 200)

    if not candles_m1 or not candles_m5:
        log_entry = {"time": datetime.now().strftime("%H:%M:%S"), "msg": "Failed to fetch candle data", "pnl": 0}
        bot_trades_log.append(log_entry)
        return log_entry

    # Extract close prices only for analysis
    closes_m1 = [c["close"] for c in candles_m1]
    closes_m5 = [c["close"] for c in candles_m5]
    current_price = closes_m1[-1]  # Latest close = current price

    # Get config
    result = await db.execute(select(BotConfig).where(BotConfig.user_id == user_id))
    cfg_row = result.scalar_one_or_none()
    config = json.loads(cfg_row.config_json) if cfg_row else {"macd_fast":4,"macd_slow":5,"macd_signal":3,"tp_percent":2.5,"sl_percent":1.5,"order_size":50,"mode":"spot","balance_type":"demo","m1":{"fast":4,"slow":5,"signal":3},"m5":{"fast":4,"slow":5,"signal":3}}

    # Init streaming MACD if needed
    if spot_macd_m1 is None:
        m1_cfg = config.get("m1", {"fast": 4, "slow": 5, "signal": 3})
        spot_macd_m1 = RealTimeMACD(fast_period=m1_cfg["fast"], slow_period=m1_cfg["slow"], signal_period=m1_cfg["signal"])
        for p in closes_m1[-50:]:
            spot_macd_m1.update(p)
    if spot_macd_m5 is None:
        m5_cfg = config.get("m5", {"fast": 4, "slow": 5, "signal": 3})
        spot_macd_m5 = RealTimeMACD(fast_period=m5_cfg["fast"], slow_period=m5_cfg["slow"], signal_period=m5_cfg["signal"])
        for p in closes_m5[-50:]:
            spot_macd_m5.update(p)
    spot_macd_m1.update(current_price)
    spot_macd_m5.update(current_price)

    # Get streaming state
    m1 = spot_macd_m1.get_state()
    m5 = spot_macd_m5.get_state()

    # Build analysis from streaming data
    m1_macd = m1.get("macd", 0)
    m5_macd = m5.get("macd", 0)
    if m1_macd > 0 and m5_macd > 0:
        aligned = True
        trade_signal = "LONG"
    elif m1_macd < 0 and m5_macd < 0:
        aligned = True
        trade_signal = "SHORT"
    else:
        aligned = False
        trade_signal = "NEUTRAL"
    analysis = {"m1": m1, "m5": m5, "aligned": aligned, "trade_signal": trade_signal}
    bot_analysis = analysis

    # Check existing position (TP/SL)
    if bot_position:
        if bot_position["side"] == "LONG":
            if current_price >= bot_position["tp"]:
                pnl = (current_price - bot_position["entry"]) * bot_position["size"]
                pnl_pct = (current_price - bot_position["entry"]) / bot_position["entry"] * 100
                trade = Trade(user_id=user_id, mode="demo", side="buy", pair=pair, price=current_price, size=bot_position["size"], pnl=round(pnl, 2), pnl_pct=round(pnl_pct, 2), status="tp_hit")
                db.add(trade)
                await db.commit()
                log_entry = {"time": datetime.now().strftime("%H:%M:%S"), "msg": f"TP HIT LONG {pair} @ ${current_price:,.2f} | PnL: ${pnl:+.2f}", "pnl": pnl}
                bot_trades_log.append(log_entry)
                bot_position = None
                return log_entry
            elif current_price <= bot_position["sl"]:
                pnl = (current_price - bot_position["entry"]) * bot_position["size"]
                pnl_pct = (current_price - bot_position["entry"]) / bot_position["entry"] * 100
                trade = Trade(user_id=user_id, mode="demo", side="buy", pair=pair, price=current_price, size=bot_position["size"], pnl=round(pnl, 2), pnl_pct=round(pnl_pct, 2), status="sl_hit")
                db.add(trade)
                await db.commit()
                log_entry = {"time": datetime.now().strftime("%H:%M:%S"), "msg": f"SL HIT LONG {pair} @ ${current_price:,.2f} | PnL: ${pnl:+.2f}", "pnl": pnl}
                bot_trades_log.append(log_entry)
                bot_position = None
                return log_entry
        elif bot_position["side"] == "SHORT":
            if current_price <= bot_position["tp"]:
                pnl = (bot_position["entry"] - current_price) * bot_position["size"]
                pnl_pct = (bot_position["entry"] - current_price) / bot_position["entry"] * 100
                trade = Trade(user_id=user_id, mode="demo", side="sell", pair=pair, price=current_price, size=bot_position["size"], pnl=round(pnl, 2), pnl_pct=round(pnl_pct, 2), status="tp_hit")
                db.add(trade)
                await db.commit()
                log_entry = {"time": datetime.now().strftime("%H:%M:%S"), "msg": f"TP HIT SHORT {pair} @ ${current_price:,.2f} | PnL: ${pnl:+.2f}", "pnl": pnl}
                bot_trades_log.append(log_entry)
                bot_position = None
                return log_entry
            elif current_price >= bot_position["sl"]:
                pnl = (bot_position["entry"] - current_price) * bot_position["size"]
                pnl_pct = (bot_position["entry"] - current_price) / bot_position["entry"] * 100
                trade = Trade(user_id=user_id, mode="demo", side="sell", pair=pair, price=current_price, size=bot_position["size"], pnl=round(pnl, 2), pnl_pct=round(pnl_pct, 2), status="sl_hit")
                db.add(trade)
                await db.commit()
                log_entry = {"time": datetime.now().strftime("%H:%M:%S"), "msg": f"SL HIT SHORT {pair} @ ${current_price:,.2f} | PnL: ${pnl:+.2f}", "pnl": pnl}
                bot_trades_log.append(log_entry)
                bot_position = None
                return log_entry

        # Still holding
        unrealized = 0
        if bot_position["side"] == "LONG":
            unrealized = (current_price - bot_position["entry"]) * bot_position["size"]
        else:
            unrealized = (bot_position["entry"] - current_price) * bot_position["size"]
        log_entry = {"time": datetime.now().strftime("%H:%M:%S"), "msg": f"Holding {bot_position['side']} @ ${bot_position['entry']:,.2f} | Now: ${current_price:,.2f} | PnL: ${unrealized:+.2f} | M1={m1.get('signal','?')} M5={m5.get('signal','?')}", "pnl": unrealized}
        bot_trades_log.append(log_entry)
        return log_entry

    # No position — check for entry signal
    can_trade, reason = should_trade(analysis, current_price, config, bot_position is not None)

    if can_trade:
        signal = analysis["trade_signal"]
        size = config.get("order_size", 50) / current_price
        m5_data = analysis.get("m5", {})
        tp, sl = calc_tp_sl(current_price, signal, config, m5_data)

        trade_mode = config.get("balance_type", "demo")
        if trade_mode == "real":
            # Use real Bitget API for execution
            user_client = await get_user_bitget(user_id, db)
            if user_client.is_configured:
                order_side = "buy" if signal == "LONG" else "sell"
                order_size = max(1, int(size * 1000))  # Convert to lots (0.001 BTC per lot)
                order_result = await user_client.futures_market_open("BTCUSDT", "long" if signal == "LONG" else "short", order_size, leverage=10)
                logger.info(f"REAL ORDER: {order_result}")
            else:
                logger.warning("Real mode but no API keys - falling back to demo")
                trade_mode = "demo"

        bot_position = {
            "side": signal,
            "entry": current_price,
            "tp": tp,
            "sl": sl,
            "size": round(size, 6),
            "time": datetime.now().strftime("%H:%M:%S"),
        }

        side_str = "BUY" if signal == "LONG" else "SELL"
        log_entry = {"time": datetime.now().strftime("%H:%M:%S"), "msg": f"{side_str} {pair} @ ${current_price:,.2f} | TP: ${tp:,.2f} SL: ${sl:,.2f} | M1={analysis['m1']['signal']} M5={analysis['m5']['signal']}", "pnl": 0}
        bot_trades_log.append(log_entry)
        return log_entry
    else:
        m1_bs = m1.get("buy_sell", "WAIT")
        m5_bs = m5.get("buy_sell", "WAIT")
        m1_mom = m1.get("momentum", "N/A")
        m5_mom = m5.get("momentum", "N/A")
        log_entry = {"time": datetime.now().strftime("%H:%M:%S"), "msg": f"Waiting... ${current_price:,.2f} | M1={m1.get('signal','?')}({m1.get('histogram',0):.4f}) {m1_bs} {m1_mom} | M5={m5.get('signal','?')}({m5.get('histogram',0):.4f}) {m5_bs} {m5_mom} | {'ALIGNED' if aligned else 'NOT ALIGNED'}", "pnl": 0}
        bot_trades_log.append(log_entry)
        return log_entry

# ===== APP =====
app = FastAPI(title="BG-BOT v5", version="5.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ===== AUTH ROUTES =====
import pandas_ta as pd_ta



@app.get("/")
async def root():
    return {"app": "BG-BOT v5", "status": "running", "docs": "/docs", "dashboard": "/dashboard"}

@app.get("/health")
async def health():
    return {"status": "ok", "version": "5.0.0", "mode": "termux", "db": "sqlite"}

@app.post("/auth/register")
async def register(body: dict, db: AsyncSession = Depends(get_db)):
    try:
        email = (body.get("email") or "").lower().strip()
        password = body.get("password") or ""
        confirm = body.get("confirm") or ""
        name = body.get("name") or ""
        if not email or not password:
            raise HTTPException(400, "Email and password required")
        if password != confirm:
            raise HTTPException(400, "Passwords do not match")
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise HTTPException(400, "Email already registered")
        user = User(email=email, name=name, password_hash=hash_password(password))
        db.add(user)
        await db.flush()
        db.add(ApiConfig(user_id=user.id, demo=True))
        default_cfg = json.dumps({"macd_fast": 4, "macd_slow": 5, "macd_signal": 3, "tp_percent": 2.5, "sl_percent": 1.5, "order_size": 50, "max_daily_loss_pct": 5.0, "max_trades_per_hour": 10})
        db.add(BotConfig(user_id=user.id, config_json=default_cfg))
        await db.commit()
        logger.info(f"Registered: {email}")
        return {"ok": True, "user_id": user.id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register error: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, str(e))

@app.post("/auth/login")
async def login(body: dict, db: AsyncSession = Depends(get_db)):
    try:
        email = (body.get("email") or "").lower().strip()
        password = body.get("password") or ""
        if not email or not password:
            raise HTTPException(400, "Email and password required")
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(401, "Account not found")
        if not verify_password(password, user.password_hash):
            raise HTTPException(401, "Wrong password")
        token = create_token(user.id, user.email)
        user.last_login = time.time()
        await db.commit()
        return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "name": user.name}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(500, str(e))

@app.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name}


# ===== TRADES ROUTES =====
@app.get("/api/trades")
async def get_trades(limit: int = Query(50, le=500), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trade).where(Trade.user_id == user.id).order_by(Trade.id.desc()).limit(limit))
    trades = result.scalars().all()
    return [
        {"id": t.id, "trade_time": str(t.trade_time), "mode": t.mode, "side": t.side,
         "pair": t.pair, "price": t.price, "size": t.size, "pnl": t.pnl,
         "pnl_pct": t.pnl_pct, "fee": t.fee, "status": t.status}
        for t in trades
    ]

@app.post("/api/trades")
async def create_trade(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    trade = Trade(
        user_id=user.id,
        mode=body.get("mode", "spot"),
        side=body.get("side", "buy"),
        pair=body.get("pair", "BTCUSDT"),
        price=body.get("price", 0),
        size=body.get("size", 0),
        pnl=body.get("pnl", 0),
        pnl_pct=body.get("pnl_pct", 0),
        fee=body.get("fee", 0),
        status=body.get("status", "simulated"),
    )
    db.add(trade)
    await db.commit()
    return {"ok": True, "trade_id": trade.id}

@app.get("/api/trades/stats")
async def get_trade_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trade).where(Trade.user_id == user.id))
    trades = result.scalars().all()
    total = len(trades)
    wins = sum(1 for t in trades if t.pnl > 0)
    losses = sum(1 for t in trades if t.pnl < 0)
    total_pnl = sum(t.pnl for t in trades)
    spot = sum(1 for t in trades if t.mode == "spot")
    perp = sum(1 for t in trades if t.mode == "perp")
    return {
        "total": total, "wins": wins, "losses": losses,
        "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
        "total_pnl": round(total_pnl, 2),
        "spot": spot, "perp": perp,
    }


# ===== BOT ROUTES =====
@app.get("/api/bot/config")
async def get_bot_config(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BotConfig).where(BotConfig.user_id == user.id))
    cfg = result.scalar_one_or_none()
    default = {"macd_fast":4,"macd_slow":5,"macd_signal":3,"tp_percent":2.5,"sl_percent":1.5,"order_size":50,"mode":"spot","balance_type":"demo","m1":{"fast":4,"slow":5,"signal":3},"m5":{"fast":4,"slow":5,"signal":3}}
    if not cfg:
        return default
    data = json.loads(cfg.config_json)
    if "m1" not in data or not isinstance(data.get("m1"), dict):
        data["m1"] = default["m1"]
    if "m5" not in data or not isinstance(data.get("m5"), dict):
        data["m5"] = default["m5"]
    return data

@app.get("/api/bot/config-current")
async def get_current_config(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BotConfig).where(BotConfig.user_id == user.id))
    cfg = result.scalar_one_or_none()
    default = {"macd_fast":4,"macd_slow":5,"macd_signal":3,"tp_percent":2.5,"sl_percent":1.5,"order_size":50,"mode":"spot","balance_type":"demo","m1":{"fast":4,"slow":5,"signal":3},"m5":{"fast":4,"slow":5,"signal":3}}
    if not cfg:
        return default
    data = json.loads(cfg.config_json)
    if "m1" not in data or not isinstance(data.get("m1"), dict):
        data["m1"] = default["m1"]
    if "m5" not in data or not isinstance(data.get("m5"), dict):
        data["m5"] = default["m5"]
    return data

@app.post("/api/bot/config")
async def update_bot_config(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Ensure M1/M5 configs are properly structured
    if "m1" not in body or not isinstance(body.get("m1"), dict):
        body["m1"] = {"fast": int(body.get("macd_fast", 4)), "slow": int(body.get("macd_slow", 5)), "signal": int(body.get("macd_signal", 3))}
    else:
        body["m1"] = {"fast": int(body["m1"].get("fast", 4)), "slow": int(body["m1"].get("slow", 5)), "signal": int(body["m1"].get("signal", 1))}
    if "m5" not in body or not isinstance(body.get("m5"), dict):
        body["m5"] = {"fast": 12, "slow": 26, "signal": 9}
    else:
        body["m5"] = {"fast": int(body["m5"].get("fast", 12)), "slow": int(body["m5"].get("slow", 26)), "signal": int(body["m5"].get("signal", 9))}
    result = await db.execute(select(BotConfig).where(BotConfig.user_id == user.id))
    cfg = result.scalar_one_or_none()
    if cfg:
        cfg.config_json = json.dumps(body)
    else:
        db.add(BotConfig(user_id=user.id, config_json=json.dumps(body)))
    await db.commit()
    global _bot_config_cache
    _bot_config_cache = {"m1": body.get("m1", {}), "m5": body.get("m5", {})}
    return {"ok": True, "msg": f"Config saved M1({body['m1']['fast']}-{body['m1']['slow']}-{body['m1']['signal']}) M5({body['m5']['fast']}-{body['m5']['slow']}-{body['m5']['signal']})"}

@app.post("/api/bot/start")
async def start_bot(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    global bot_running, bot_trades_log, bot_position, bot_analysis
    if bot_running:
        return {"ok": True, "status": "already_running", "msg": "Bot already running"}
    bot_running = True
    bot_trades_log = []

# ===== REAL-TIME STREAMING ENGINE =====
from trade_engine import RealTimeMACD

bws = BitgetWebSocket(m1_fast=4, m1_slow=5, m1_sig=3, m5_fast=4, m5_slow=5, m5_sig=3)

ws_price = 0.0
ws_connected = False
ws_last_tick = 0



# ===== ALWAYS-ON MARKET ANALYSIS =====

@app.post("/api/bot/stop")
async def stop_bot(user: User = Depends(get_current_user)):
    global bot_running, bot_position, bot_analysis
    bot_running = False
    pos_info = f" (closing {bot_position['side']} @ {bot_position['entry']})" if bot_position else ""
    bot_position = None
    bot_analysis = {"m1": {}, "m5": {}, "aligned": False, "trade_signal": "NEUTRAL"}

# ===== ALWAYS-ON MARKET ANALYSIS =====

@app.get("/api/bot/status")
async def bot_status(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    global bot_running, bot_trades_log, bot_position, bot_analysis, spot_macd_m1, spot_macd_m5
    client = BitgetClient()
    ticker = await client.get_ticker("BTCUSDT")
    price = ticker.get("price", 0)

    # Read config for mode and balance_type
    try:
        result = await db.execute(select(BotConfig).where(BotConfig.user_id == user.id))
        cfg_row = result.scalar_one_or_none()
        status_config = json.loads(cfg_row.config_json) if cfg_row else {}
    except:
        status_config = {}
    status_mode = status_config.get("mode", "spot")
    status_bal = status_config.get("balance_type", "demo")

    position_info = None
    if bot_position:
        unrealized = 0
        if bot_position["side"] == "LONG":
            unrealized = (price - bot_position["entry"]) * bot_position["size"]
        else:
            unrealized = (bot_position["entry"] - price) * bot_position["size"]
        position_info = {
            "side": bot_position["side"],
            "entry": bot_position["entry"],
            "tp": bot_position["tp"],
            "sl": bot_position["sl"],
            "current_price": price,
            "unrealized_pnl": round(unrealized, 2),
            "pnl_pct": round(unrealized / (bot_position["entry"] * bot_position["size"]) * 100, 2) if bot_position.get("size", 0) > 0 else 0,
        }

    # Get streaming MACD state (live data)
    m1 = spot_macd_m1.get_state() if spot_macd_m1 and spot_macd_m1.initialized else dict(bot_analysis.get("m1", {}))
    m5 = spot_macd_m5.get_state() if spot_macd_m5 and spot_macd_m5.initialized else dict(bot_analysis.get("m5", {}))

    # Ensure all required fields with defaults
    defaults = {"signal": "-", "buy_sell": "WAIT", "macd": 0, "signal_line": 0,
                "histogram": 0, "ema_fast": 0, "ema_slow": 0,
                "macd_pct_from_zero": 0, "hist_pct_from_zero": 0, "signal_line_pct": 0,
                "price": price, "candles": 0,
                "macd_history": [], "hist_history": [], "signal_history": [], "close_history": [],
                "config": {"fast": 4, "slow": 5, "signal": 3}}
    for k, v in defaults.items():
        if k not in m1:
            m1[k] = v
        if k not in m5:
            m5[k] = v

    return {
        "running": bot_running,
        "mode": status_mode,
        "balance_type": status_bal,
        "symbol": "BTCUSDT",
        "balance": 10000.00 if status_bal == "demo" else -1,
        "current_price": price,
        "position": position_info,
        "m1": m1 if isinstance(m1, dict) else {},
        "m5": m5 if isinstance(m5, dict) else {},
        "aligned": bot_analysis.get("aligned", False),
        "trade_signal": bot_analysis.get("trade_signal", "NEUTRAL"),
        "positions": [position_info] if position_info else [],
        "logs": bot_trades_log[-30:],
        "ws_connected": bws.connected,
        "ws_price": bws.price,
        "ws_last_tick": bws.last_tick,
    }


# ===== API CONFIG ROUTES =====
@app.get("/api/config")
async def get_api_config(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiConfig).where(ApiConfig.user_id == user.id))
    cfg = result.scalar_one_or_none()
    if not cfg:
        return {"api_key": "", "demo": True}
    return {"api_key": cfg.api_key[:8] + "..." if cfg.api_key else "", "demo": cfg.demo}

@app.post("/api/config")
async def update_api_config(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiConfig).where(ApiConfig.user_id == user.id))
    cfg = result.scalar_one_or_none()
    if cfg:
        cfg.api_key = body.get("api_key", cfg.api_key)
        cfg.api_secret = body.get("api_secret", cfg.api_secret)
        cfg.api_passphrase = body.get("api_passphrase", cfg.api_passphrase)
        cfg.demo = body.get("demo", cfg.demo)
    else:
        db.add(ApiConfig(user_id=user.id, api_key=body.get("api_key", ""), api_secret=body.get("api_secret", ""), demo=body.get("demo", True)))
    await db.commit()
    return {"ok": True}


# ===== BACKTEST ROUTES =====


@app.get("/api/trades/export")
async def export_trades_csv(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    import csv, io
    from fastapi.responses import StreamingResponse
    result = await db.execute(select(Trade).where(Trade.user_id == user.id).order_by(Trade.id.desc()))
    trades = result.scalars().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","time","mode","side","pair","price","size","pnl","pnl_pct","status"])
    for t in trades:
        writer.writerow([t.id, str(t.trade_time), t.mode, t.side, t.pair, t.price, t.size, t.pnl, t.pnl_pct, t.status])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trades.csv"})

# ===== MARKET DATA (Real Bitget) =====

# ===== MARKET DATA (Real Bitget) =====
@app.get("/api/market/ticker")
async def get_ticker(symbol: str = Query("BTCUSDT")):
    client = BitgetClient()
    return await client.get_ticker(symbol)

@app.get("/api/market/klines")
async def get_klines(symbol: str = Query("BTCUSDT"), granularity: str = Query("5min"), limit: int = Query(100, le=500)):
    client = BitgetClient()
    candles = await client.get_klines(symbol, granularity, limit)
    return {"symbol": symbol, "granularity": granularity, "candles": candles}

@app.get("/api/market/orderbook")
async def get_orderbook(symbol: str = Query("BTCUSDT"), limit: int = Query(20, le=50)):
    client = BitgetClient()
    return await client.get_orderbook(symbol, limit)


@app.get("/api/market/indicators")
async def get_indicators(symbol: str = Query("BTCUSDT"), granularity: str = Query("1min"), limit: int = Query(100, le=500)):
    """Get klines with BB, MACD, RSI indicators using config params"""
    client = BitgetClient()
    candles = await client.get_klines(symbol, granularity, limit)
    if not candles:
        return {"symbol": symbol, "granularity": granularity, "candles": []}
    import pandas as pd
    is_m1 = granularity in ["1min", "1m"]
    bb_len = _config_store.get("m1_bb_length", 6) if is_m1 else _config_store.get("m5_bb_length", 6)
    bb_std = float(_config_store.get("m1_bb_std", 1.2)) if is_m1 else float(_config_store.get("m5_bb_std", 1.2))
    rsi_len = _config_store.get("m1_rsi_length", 6) if is_m1 else _config_store.get("m5_rsi_length", 6)
    m1c = _config_store.get("m1", {})
    m5c = _config_store.get("m5", {})
    m_fast = m1c.get("fast", 4) if is_m1 else m5c.get("fast", 4)
    m_slow = m1c.get("slow", 5) if is_m1 else m5c.get("slow", 5)
    m_sig = m1c.get("signal", 3) if is_m1 else m5c.get("signal", 3)
    df = pd.DataFrame(candles)
    # Ensure numeric types
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    close = df["close"]
    # Always init columns first
    df["bb_lower"] = 0.0; df["bb_mid"] = 0.0; df["bb_upper"] = 0.0
    df["macd_line"] = 0.0; df["macd_hist"] = 0.0; df["macd_signal"] = 0.0
    df["rsi"] = 50.0
    # BB (only if enough data)
    if len(close) >= bb_len:
        try:
            bb = pd_ta.bbands(close, length=bb_len, std=bb_std)
            if bb is not None and len(bb) > 0:
                cols = bb.columns.tolist()
                if len(cols) >= 3:
                    df["bb_lower"] = pd.to_numeric(bb[cols[0]], errors="coerce").fillna(0)
                    df["bb_mid"] = pd.to_numeric(bb[cols[1]], errors="coerce").fillna(0)
                    df["bb_upper"] = pd.to_numeric(bb[cols[2]], errors="coerce").fillna(0)
        except Exception as e:
            logger.error(f"BB calc error: {e}")
    # MACD (only if enough data)
    if len(close) >= m_slow:
        try:
            macd = pd_ta.macd(close, fast=m_fast, slow=m_slow, signal=m_sig)
            if macd is not None and len(macd) > 0:
                cols = macd.columns.tolist()
                if len(cols) >= 3:
                    df["macd_line"] = pd.to_numeric(macd[cols[0]], errors="coerce").fillna(0)
                    df["macd_hist"] = pd.to_numeric(macd[cols[1]], errors="coerce").fillna(0)
                    df["macd_signal"] = pd.to_numeric(macd[cols[2]], errors="coerce").fillna(0)
        except Exception as e:
            logger.error(f"MACD calc error: {e}")
    # RSI (only if enough data)
    if len(close) >= rsi_len:
        try:
            rsi = pd_ta.rsi(close, length=rsi_len)
            if rsi is not None and len(rsi) > 0:
                df["rsi"] = pd.to_numeric(rsi, errors="coerce").fillna(50)
        except Exception as e:
            logger.error(f"RSI calc error: {e}")
    df = df.fillna(0)
    records = df.to_dict("records")
    for r in records:
        v = r.get("rsi", 50)
        if v <= 28: r["rsi_zone"] = "oversold"
        elif v <= 42: r["rsi_zone"] = "weak"
        elif v <= 56: r["rsi_zone"] = "neutral"
        elif v <= 70: r["rsi_zone"] = "strong"
        elif v <= 84: r["rsi_zone"] = "overbought"
        else: r["rsi_zone"] = "extreme_overbought"
    return {"symbol": symbol, "granularity": granularity, "candles": records, "config": {"bb_length": bb_len, "bb_std": bb_std, "rsi_length": rsi_len, "macd_fast": m_fast, "macd_slow": m_slow, "macd_signal": m_sig, "m1_bb_enabled": _config_store.get("m1_bb_enabled", True), "m1_macd_enabled": _config_store.get("m1_macd_enabled", True), "m1_rsi_enabled": _config_store.get("m1_rsi_enabled", True), "m5_bb_enabled": _config_store.get("m5_bb_enabled", True), "m5_macd_enabled": _config_store.get("m5_macd_enabled", True), "m5_rsi_enabled": _config_store.get("m5_rsi_enabled", True)}}



@app.get("/api/market/signals")
async def get_signals(symbol: str = Query("BTCUSDT")):
    """Dual-timeframe M1+M5 signal analysis using config params"""
    client = BitgetClient()
    import pandas as pd
    m1cfg = _config_store.get("m1", {})
    m5cfg = _config_store.get("m5", {})
    m1_bb_len = _config_store.get("m1_bb_length", 6)
    m1_bb_std = float(_config_store.get("m1_bb_std", 1.2))
    m1_rsi_len = _config_store.get("m1_rsi_length", 6)
    m5_bb_len = _config_store.get("m5_bb_length", 6)
    m5_bb_std = float(_config_store.get("m5_bb_std", 1.2))
    m5_rsi_len = _config_store.get("m5_rsi_length", 6)
    m1f = m1cfg.get("fast", 4)
    m1s = m1cfg.get("slow", 5)
    m1g = m1cfg.get("signal", 3)
    m5f = m5cfg.get("fast", 4)
    m5s = m5cfg.get("slow", 5)
    m5g = m5cfg.get("signal", 3)

    try:
        c1 = await client.get_klines(symbol, "1min", 200)
        c5 = await client.get_klines(symbol, "5min", 200)
        if not c1 or not c5:
            return {"signals": [], "m1_bb": {"bb_length": m1_bb_len, "bb_std": m1_bb_std, "rsi_length": m1_rsi_len}, "m5_bb": {"bb_length": m5_bb_len, "bb_std": m5_bb_std, "rsi_length": m5_rsi_len}}
    except Exception as e:
        return {"error": str(e), "signals": [], "m1_bb": {}, "m5_bb": {}}

    def calc(klines, fast, slow, sig, bb_l, bb_s, rsi_l):
        df = pd.DataFrame(klines)
        for col in ["open","high","low","close","volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        close = df["close"]
        try:
            bb = pd_ta.bbands(close, length=bb_l, std=bb_s)
            if bb is not None:
                cols = bb.columns.tolist()
                df["bb_upper"] = bb[cols[0]].fillna(0)
                df["bb_mid"] = bb[cols[1]].fillna(0)
                df["bb_lower"] = bb[cols[2]].fillna(0)
            else:
                df["bb_upper"] = df["bb_mid"] = df["bb_lower"] = 0
        except Exception:
            df["bb_upper"] = df["bb_mid"] = df["bb_lower"] = 0
        try:
            macd = pd_ta.macd(close, fast=fast, slow=slow, signal=sig)
            if macd is not None:
                cols = macd.columns.tolist()
                df["macd_line"] = macd[cols[0]].fillna(0)
                df["macd_hist"] = macd[cols[1]].fillna(0)
                df["macd_signal"] = macd[cols[2]].fillna(0)
            else:
                df["macd_line"] = df["macd_hist"] = df["macd_signal"] = 0
        except Exception:
            df["macd_line"] = df["macd_hist"] = df["macd_signal"] = 0
        try:
            rsi = pd_ta.rsi(close, length=rsi_l)
            if rsi is not None:
                df["rsi"] = rsi.fillna(50)
            else:
                df["rsi"] = 50
        except Exception:
            df["rsi"] = 50
        df = df.fillna(0)
        return df

    try:
        df1 = calc(c1, m1f, m1s, m1g, m1_bb_len, m1_bb_std, m1_rsi_len)
        df5 = calc(c5, m5f, m5s, m5g, m5_bb_len, m5_bb_std, m5_rsi_len)
    except Exception as e:
        logger.error(f"signals calc error: {e}")
        return {"error": str(e), "signals": [], "m1_bb": {"bb_length": m1_bb_len, "bb_std": m1_bb_std, "rsi_length": m1_rsi_len}, "m5_bb": {"bb_length": m5_bb_len, "bb_std": m5_bb_std, "rsi_length": m5_rsi_len}}

    signals = []
    # Analyze last 20 M1 candles
    for i in range(max(1, len(df1)-20), len(df1)):
        row = df1.iloc[i]
        prev = df1.iloc[i-1]
        ts = row.get("time", 0)
        price = row["close"]
        rsi_val = row["rsi"]
        macd_line = row["macd_line"]
        macd_sig = row["macd_signal"]
        macd_hist = row["macd_hist"]
        bb_up = row["bb_upper"]
        bb_low = row["bb_lower"]
        bb_mid = row["bb_mid"]

        # Find closest M5 candle
        closest_m5 = df5.iloc[-1]
        for _, m5r in df5.iterrows():
            if abs(m5r["time"] - ts) < abs(closest_m5["time"] - ts):
                closest_m5 = m5r

        m5_macd = closest_m5["macd_line"]
        m5_sig = closest_m5["macd_signal"]
        m5_rsi = closest_m5["rsi"]
        m5_trend = "UP" if m5_macd > m5_sig else "DOWN"

        # MACD crossover detection
        macd_cross_up = prev["macd_line"] < prev["macd_signal"] and macd_line > macd_sig
        macd_cross_down = prev["macd_line"] > prev["macd_signal"] and macd_line < macd_sig

        # BB touch detection
        bb_lower_touch = price <= bb_low and bb_low > 0
        bb_upper_touch = price >= bb_up and bb_up > 0

        # RSI conditions
        rsi_oversold = rsi_val < 28
        rsi_overbought = rsi_val > 70

        # STRONG BUY: M1 buy + M5 uptrend
        if (macd_cross_up or bb_lower_touch) and m5_trend == "UP":
            strength = "STRONG" if rsi_oversold else "MODERATE"
            signals.append({"time": ts, "type": "BUY", "strength": strength, "price": price,
                "m1": {"rsi": round(rsi_val,1), "macd": round(macd_line,6), "signal": round(macd_sig,6), "bb_upper": round(bb_up,2), "bb_lower": round(bb_low,2)},
                "m5": {"trend": m5_trend, "rsi": round(m5_rsi,1), "macd": round(m5_macd,6)},
                "reason": ("MACD cross up + M5 uptrend" if macd_cross_up else "BB lower touch + M5 uptrend") + (" + RSI oversold" if rsi_oversold else "")})

        # STRONG SELL: M1 sell + M5 downtrend
        elif (macd_cross_down or bb_upper_touch) and m5_trend == "DOWN":
            strength = "STRONG" if rsi_overbought else "MODERATE"
            signals.append({"time": ts, "type": "SELL", "strength": strength, "price": price,
                "m1": {"rsi": round(rsi_val,1), "macd": round(macd_line,6), "signal": round(macd_sig,6), "bb_upper": round(bb_up,2), "bb_lower": round(bb_low,2)},
                "m5": {"trend": m5_trend, "rsi": round(m5_rsi,1), "macd": round(m5_macd,6)},
                "reason": ("MACD cross down + M5 downtrend" if macd_cross_down else "BB upper touch + M5 downtrend") + (" + RSI overbought" if rsi_overbought else "")})

    # Current state
    last1 = df1.iloc[-1]
    last5 = df5.iloc[-1]
    current = {
        "price": last1["close"],
        "m1": {"rsi": round(last1["rsi"],1), "macd": round(last1["macd_line"],6), "macd_signal": round(last1["macd_signal"],6), "macd_hist": round(last1["macd_hist"],6), "bb_upper": round(last1["bb_upper"],2), "bb_mid": round(last1["bb_mid"],2), "bb_lower": round(last1["bb_lower"],2)},
        "m5": {"rsi": round(last5["rsi"],1), "macd": round(last5["macd_line"],6), "macd_signal": round(last5["macd_signal"],6), "macd_hist": round(last5["macd_hist"],6), "trend": "UP" if last5["macd_line"] > last5["macd_signal"] else "DOWN"},
        "config": {"bb_length": m1_bb_len, "bb_std": m1_bb_std, "rsi_length": m1_rsi_len, "m1": str(m1f)+"-"+str(m1s)+"-"+str(m1g), "m5": str(m5f)+"-"+str(m5s)+"-"+str(m5g)}
    }
    return {"symbol": symbol, "signals": signals[-10:], "current": current, "m1_bb": {"bb_length": m1_bb_len, "bb_std": m1_bb_std, "rsi_length": m1_rsi_len}, "m5_bb": {"bb_length": m5_bb_len, "bb_std": m5_bb_std, "rsi_length": m5_rsi_len}}


@app.get("/api/market/spot-symbols")
async def get_spot_symbols():
    """Top 100 spot pairs sorted by 24h USDT volume (market cap proxy)"""
    try:
        data = await BitgetClient()._request("GET", "/api/v2/spot/market/tickers")
        if data.get("code") == "00000":
            pairs = []
            for s in data.get("data", []):
                sym = s.get("symbol", "")
                if sym.endswith("USDT"):
                    try:
                        vol = float(s.get("usdtVolume", 0) or s.get("quoteVolume24h", 0) or s.get("turnover24h", 0) or 0)
                    except (ValueError, TypeError):
                        vol = 0
                    pairs.append((sym, vol))
            pairs.sort(key=lambda x: x[1], reverse=True)
            symbols = [p[0] for p in pairs[:100]]
            if symbols:
                logger.info(f"spot-symbols: {len(symbols)} loaded, top={symbols[0]}")
                return {"symbols": symbols}
    except Exception as e:
        logger.error(f"spot-symbols: {e}")
    return {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]}

@app.get("/api/market/futures-symbols")
async def get_futures_symbols():
    """Top 100 perpetual futures pairs sorted by 24h USDT volume (market cap proxy)"""
    try:
        data = await BitgetClient()._request("GET", "/api/v2/mix/market/tickers?productType=USDT-FUTURES")
        if data.get("code") == "00000":
            pairs = []
            for s in data.get("data", []):
                sym = s.get("symbol", "")
                if sym.endswith("USDT"):
                    try:
                        vol = float(s.get("usdtVolume", 0) or s.get("quoteVolume24h", 0) or s.get("turnover24h", 0) or 0)
                    except (ValueError, TypeError):
                        vol = 0
                    pairs.append((sym, vol))
            pairs.sort(key=lambda x: x[1], reverse=True)
            symbols = [p[0] for p in pairs[:100]]
            if symbols:
                logger.info(f"futures-symbols: {len(symbols)} loaded, top={symbols[0]}")
                return {"symbols": symbols}
    except Exception as e:
        logger.error(f"futures-symbols: {e}")
    return {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]}

@app.get("/api/market/symbols")
async def get_symbols():
    data = await BitgetClient()._request("GET", "/api/v2/spot/public/symbols")
    if data.get("code") == "00000":
        symbols = [s.get("symbol", "") for s in data.get("data", []) if s.get("symbol", "").endswith("USDT")][:50]
        return {"symbols": symbols if symbols else ["BTCUSDT", "ETHUSDT", "SOLUSDT"]}
    return {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]}


# ===== SPOT TRADING =====
@app.post("/api/spot/market-buy")
async def spot_market_buy(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    symbol = body.get("symbol", "BTCUSDT")
    amount = body.get("amount", 0)
    if amount <= 0:
        raise HTTPException(400, "Amount must be > 0")
    client = await get_user_bitget(user.id, db)
    result = await client.spot_market_buy(symbol, amount)
    return result

@app.post("/api/spot/market-sell")
async def spot_market_sell(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    symbol = body.get("symbol", "BTCUSDT")
    size = body.get("size", 0)
    if size <= 0:
        raise HTTPException(400, "Size must be > 0")
    client = await get_user_bitget(user.id, db)
    result = await client.spot_market_sell(symbol, size)
    return result

@app.post("/api/spot/limit-buy")
async def spot_limit_buy(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    symbol = body.get("symbol", "BTCUSDT")
    size = body.get("size", 0)
    price = body.get("price", 0)
    if size <= 0 or price <= 0:
        raise HTTPException(400, "Size and price must be > 0")
    client = await get_user_bitget(user.id, db)
    result = await client.spot_limit_buy(symbol, size, price)
    return result

@app.post("/api/spot/limit-sell")
async def spot_limit_sell(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    symbol = body.get("symbol", "BTCUSDT")
    size = body.get("size", 0)
    price = body.get("price", 0)
    if size <= 0 or price <= 0:
        raise HTTPException(400, "Size and price must be > 0")
    client = await get_user_bitget(user.id, db)
    result = await client.spot_limit_sell(symbol, size, price)
    return result

@app.post("/api/spot/stop-limit")
async def spot_stop_limit(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    symbol = body.get("symbol", "BTCUSDT")
    side = body.get("side", "buy")
    size = body.get("size", 0)
    price = body.get("price", 0)
    trigger_price = body.get("trigger_price", 0)
    if size <= 0 or price <= 0 or trigger_price <= 0:
        raise HTTPException(400, "Size, price and trigger_price must be > 0")
    client = await get_user_bitget(user.id, db)
    result = await client.spot_stop_limit(symbol, side, size, price, trigger_price)
    return result

@app.post("/api/spot/cancel")
async def spot_cancel(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    symbol = body.get("symbol", "BTCUSDT")
    order_id = body.get("order_id", "")
    if not order_id:
        raise HTTPException(400, "order_id required")
    client = await get_user_bitget(user.id, db)
    return await client.spot_cancel_order(symbol, order_id)

@app.get("/api/spot/account")
async def spot_account(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await get_user_bitget(user.id, db)
    return await client.get_spot_account()

@app.get("/api/spot/orders")
async def spot_orders(symbol: str = Query("BTCUSDT"), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await get_user_bitget(user.id, db)
    return await client.get_spot_orders(symbol)

@app.get("/api/spot/history")
async def spot_history(symbol: str = Query("BTCUSDT"), limit: int = Query(20), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await get_user_bitget(user.id, db)
    return await client.get_spot_history(symbol, limit)


# ===== PERPETUAL (FUTURES) TRADING =====
@app.post("/api/futures/set-leverage")
async def futures_set_leverage(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    symbol = body.get("symbol", "BTCUSDT")
    leverage = body.get("leverage", 10)
    margin_mode = body.get("margin_mode", "crossed")
    if leverage < 1 or leverage > 125:
        raise HTTPException(400, "Leverage must be 1-125")
    client = await get_user_bitget(user.id, db)
    return await client.futures_set_leverage(symbol, leverage, margin_mode)

@app.post("/api/futures/market-open")
async def futures_market_open(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    symbol = body.get("symbol", "BTCUSDT")
    side = body.get("side", "open_long")
    size = body.get("size", 0)
    leverage = body.get("leverage", 10)
    margin_mode = body.get("margin_mode", "crossed")
    if size <= 0:
        raise HTTPException(400, "Size must be > 0")
    if side not in ["open_long", "open_short"]:
        raise HTTPException(400, "Side must be open_long or open_short")
    client = await get_user_bitget(user.id, db)
    result = await client.futures_market_open(symbol, side, size, leverage, margin_mode)
    if result.get("ok") and body.get("tp_price") or body.get("sl_price"):
        hold_side = "long" if side == "open_long" else "short"
        await client.futures_stop_tp_sl(symbol, hold_side, size, body.get("tp_price"), body.get("sl_price"))
    return result

@app.post("/api/futures/market-close")
async def futures_market_close(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    symbol = body.get("symbol", "BTCUSDT")
    side = body.get("side", "long")
    size = body.get("size", 0)
    leverage = body.get("leverage", 10)
    margin_mode = body.get("margin_mode", "crossed")
    if size <= 0:
        raise HTTPException(400, "Size must be > 0")
    client = await get_user_bitget(user.id, db)
    return await client.futures_market_close(symbol, side, size, leverage, margin_mode)

@app.post("/api/futures/limit-open")
async def futures_limit_open(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    symbol = body.get("symbol", "BTCUSDT")
    side = body.get("side", "open_long")
    size = body.get("size", 0)
    price = body.get("price", 0)
    leverage = body.get("leverage", 10)
    margin_mode = body.get("margin_mode", "crossed")
    if size <= 0 or price <= 0:
        raise HTTPException(400, "Size and price must be > 0")
    client = await get_user_bitget(user.id, db)
    return await client.futures_limit_open(symbol, side, size, price, leverage, margin_mode)

@app.post("/api/futures/cancel")
async def futures_cancel(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    symbol = body.get("symbol", "BTCUSDT")
    order_id = body.get("order_id", "")
    if not order_id:
        raise HTTPException(400, "order_id required")
    client = await get_user_bitget(user.id, db)
    return await client.futures_cancel_order(symbol, order_id)

@app.get("/api/futures/account")
async def futures_account():
    """Futures account - uses demo balance if no API keys"""
    try:
        client = BitgetClient()
        result = await client.get_futures_account()
        return result
    except Exception as e:
        logger.error(f"futures/account: {e}")
        return {"assets": [], "total_usdt": _config_store.get("balance", 10000), "error": str(e)}

@app.get("/api/futures/positions")
async def futures_positions(symbol: str = Query("BTCUSDT")):
    try:
        client = BitgetClient()
        return await client.get_futures_positions(symbol)
    except Exception as e:
        logger.error(f"futures/positions: {e}")
        return {"positions": []}

@app.get("/api/futures/orders")
async def futures_orders(symbol: str = Query("BTCUSDT")):
    try:
        client = BitgetClient()
        return await client.get_futures_orders(symbol)
    except Exception as e:
        logger.error(f"futures/orders: {e}")
        return {"orders": []}

@app.get("/api/futures/history")
async def futures_history(symbol: str = Query("BTCUSDT"), limit: int = Query(20), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await get_user_bitget(user.id, db)
    return await client.get_futures_history(symbol, limit)

@app.get("/api/futures/ticker")
async def futures_ticker(symbol: str = Query("BTCUSDT")):
    """Futures ticker with bid/ask from WS engine"""
    client = BitgetClient()
    result = await client.get_futures_ticker(symbol)
    # Merge with WS price if available
    if bws.price > 0:
        result["price"] = bws.price
        result["ws_connected"] = bws.connected
    # Add BB data
    analysis = bws.get_analysis()
    bb = analysis.get("bb", {})
    result["bb"] = bb
    result["ticker"] = analysis.get("ticker", {})
    return result

@app.get("/api/futures/klines")
async def futures_klines(symbol: str = Query("BTCUSDT"), granularity: str = Query("5min"), limit: int = Query(100, le=500)):
    client = BitgetClient()
    candles = await client.get_futures_klines(symbol, granularity, limit)
    return {"symbol": symbol, "granularity": granularity, "candles": candles}

# ===== PERPETUAL BOT ROUTES =====
@app.post("/api/perp/start")
async def perp_start(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiConfig).where(ApiConfig.user_id == user.id))
    cfg = result.scalar_one_or_none()
    api_key = cfg.api_key if cfg and cfg.api_key else ""
    api_secret = cfg.api_secret if cfg and cfg.api_secret else ""
    passphrase = cfg.api_passphrase if cfg and cfg.api_passphrase else ""
    use_real = bool(api_key)
    # Pass config MACD params to perp engine
    m1_cfg = _config_store.get("m1", {})
    m5_cfg = _config_store.get("m5", {})
    res = await start_perp_bot(api_key, api_secret, passphrase, use_real,
        m1_fast=m1_cfg.get("fast", 4), m1_slow=m1_cfg.get("slow", 5), m1_sig=m1_cfg.get("signal", 3),
        m5_fast=m5_cfg.get("fast", 4), m5_slow=m5_cfg.get("slow", 5), m5_sig=m5_cfg.get("signal", 3))
    return res

@app.post("/api/perp/stop")
async def perp_stop(user: User = Depends(get_current_user)):
    return await stop_perp_bot()

@app.get("/api/perp/status")
async def perp_status():
    """Public perp status with BB data from WS engine"""
    status = get_perp_status()
    # Inject BB + ticker from WS engine (reuses Market data)
    analysis = bws.get_analysis()
    bb = analysis.get("bb", {})
    ticker = analysis.get("ticker", {})
    status["bb"] = bb
    status["ticker"] = ticker
    status["market_price"] = bws.price
    status["market_connected"] = bws.connected
    status["m1_config"] = {
        "bb_length": _config_store.get("m1_bb_length", 6),
        "bb_std": _config_store.get("m1_bb_std", 1.2),
        "rsi_length": _config_store.get("m1_rsi_length", 6),
        "macd": str(_config_store.get("m1",{}).get("fast",4))+"-"+str(_config_store.get("m1",{}).get("slow",5))+"-"+str(_config_store.get("m1",{}).get("signal",3))
    }
    status["m5_config"] = {
        "bb_length": _config_store.get("m5_bb_length", 6),
        "bb_std": _config_store.get("m5_bb_std", 1.2),
        "rsi_length": _config_store.get("m5_rsi_length", 6),
        "macd": str(_config_store.get("m5",{}).get("fast",4))+"-"+str(_config_store.get("m5",{}).get("slow",5))+"-"+str(_config_store.get("m5",{}).get("signal",3))
    }
    return status



@app.get("/api/market/analysis")
async def get_market_analysis():
    """Always-on MACD analysis, returns current state"""
    return {
        "m1": bot_analysis.get("m1", {}),
        "m5": bot_analysis.get("m5", {}),
        "aligned": bot_analysis.get("aligned", False),
        "trade_signal": bot_analysis.get("trade_signal", "NEUTRAL"),
        "timestamp": bot_analysis.get("timestamp", ""),
    }

@app.get("/api/bot/status-public")
async def bot_status_public():
    """Public bot status - no auth required"""
    global bot_running, bot_trades_log, bot_position, bot_analysis
    price = bws.price if bws.price > 0 else (ws_price if ws_price > 0 else 0)
    

    position_info = None
    if bot_position:
        unrealized = 0
        if bot_position["side"] == "LONG":
            unrealized = (price - bot_position["entry"]) * bot_position["size"]
        else:
            unrealized = (bot_position["entry"] - price) * bot_position["size"]
        position_info = {
            "side": bot_position["side"],
            "entry": bot_position["entry"],
            "tp": bot_position["tp"],
            "sl": bot_position["sl"],
            "unrealized_pnl": round(unrealized, 2),
        }

    m1 = dict(bot_analysis.get("m1", {}))
    m5 = dict(bot_analysis.get("m5", {}))
    defaults = {"signal": "-", "buy_sell": "WAIT", "macd": 0, "signal_line": 0,
                "histogram": 0, "macd_history": [], "hist_history": [],
                "signal_history": [], "close_history": [], "momentum": "N/A",
                "volatility": 0, "macd_pct_from_zero": 0, "hist_pct_from_zero": 0,
                "ema_fast": 0, "ema_slow": 0, "candles": 0}
    for k, v in defaults.items():
        if k not in m1: m1[k] = v
        if k not in m5: m5[k] = v

    return {
        "running": bot_running,
        "current_price": price,
        "balance": round(bot_initial_balance + bot_realized_pnl + (position_info["unrealized_pnl"] if position_info else 0), 2),
        "mode": "spot",
        "balance_type": "demo",
        "position": position_info,
        "m1": m1,
        "m5": m5,
        "aligned": bot_analysis.get("aligned", False),
        "trade_signal": bot_analysis.get("trade_signal", "NEUTRAL"),
                "initial_balance": bot_initial_balance,
        "realized_pnl": round(bot_realized_pnl, 2),
        "unrealized_pnl": round(position_info["unrealized_pnl"] if position_info else 0, 2),
        "total_pnl": round(bot_realized_pnl + (position_info["unrealized_pnl"] if position_info else 0), 2),
"logs": bot_trades_log[-30:],
        "ws_connected": bws.connected,
        "ws_price": bws.price,
        "ws_last_tick": bws.last_tick,
    }




# ===== MODULE-LEVEL BOT LOOP =====

async def _bws_updater():
    """Sync BitgetWebSocket state to bot globals"""
    global ws_price, ws_connected, ws_last_tick, bot_analysis
    logger.info("BWS updater started")
    while True:
        try:
            ws_price = bws.price
            ws_connected = bws.connected
            ws_last_tick = bws.last_tick
            bot_analysis = bws.get_analysis()
        except Exception as e:
            logger.error(f"BWS updater: {e}")
        await asyncio.sleep(1)

async def _bot_trade_loop():
    """Auto-trade loop - runs at module level"""
    global bot_running, bot_trades_log, bot_position, bot_analysis, bot_realized_pnl, ws_price
    tick_count = 0
    logger.info("_bot_trade_loop STARTED")
    bot_trades_log.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": "Bot started - monitoring market", "pnl": 0})

    while bot_running:
        try:
            price = ws_price
            if price <= 0:
                if tick_count % 10 == 0:
                    bot_trades_log.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": "Waiting for price...", "pnl": 0})
                await asyncio.sleep(1)
                tick_count += 1
                continue

            m1 = bot_analysis.get("m1", {})
            m5 = bot_analysis.get("m5", {})
            signal = bot_analysis.get("trade_signal", "NEUTRAL")
            aligned = bot_analysis.get("aligned", False)
            m1_signal = m1.get("buy_sell", "?")
            m5_signal = m5.get("buy_sell", "?")
            m1_macd = m1.get("macd", 0)

            tick_count += 1

            # Log every 3 seconds
            if tick_count % 3 == 0:
                bot_trades_log.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "msg": f"#{tick_count} ${price:,.2f} | M1={m1_signal} M5={m5_signal} | Signal={signal} | {'ALIGNED' if aligned else 'NOT aligned'}",
                    "pnl": 0,
                })

            # Open position when aligned
            if not bot_position and aligned and signal in ["LONG", "SHORT"]:
                side = signal
                entry = price
                if side == "LONG":
                    tp = entry * 1.006
                    sl = entry * 0.997
                else:
                    tp = entry * 0.994
                    sl = entry * 1.003

                bot_position = {
                    "side": side, "entry": round(entry, 2),
                    "tp": round(tp, 2), "sl": round(sl, 2),
                    "size": 0.001,
                    "open_time": datetime.now().strftime("%H:%M:%S"),
                }
                bot_trades_log.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "msg": f"OPEN {side} @ ${entry:,.2f} | TP=${tp:,.2f} SL=${sl:,.2f}",
                    "pnl": 0,
                })

            # Check TP/SL
            if bot_position:
                pos = bot_position
                hit = False
                pnl = 0
                if pos["side"] == "LONG":
                    if price >= pos["tp"]:
                        pnl = (pos["tp"] - pos["entry"]) * pos["size"]
                        bot_trades_log.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": f"TP HIT LONG +${pnl:.2f}", "pnl": round(pnl, 2)})
                        hit = True
                    elif price <= pos["sl"]:
                        pnl = (pos["sl"] - pos["entry"]) * pos["size"]
                        bot_trades_log.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": f"SL HIT LONG ${pnl:.2f}", "pnl": round(pnl, 2)})
                        hit = True
                else:
                    if price <= pos["tp"]:
                        pnl = (pos["entry"] - pos["tp"]) * pos["size"]
                        bot_trades_log.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": f"TP HIT SHORT +${pnl:.2f}", "pnl": round(pnl, 2)})
                        hit = True
                    elif price >= pos["sl"]:
                        pnl = (pos["entry"] - pos["sl"]) * pos["size"]
                        bot_trades_log.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": f"SL HIT SHORT ${pnl:.2f}", "pnl": round(pnl, 2)})
                        hit = True

                if hit:
                    bot_realized_pnl += pnl
                    bot_position = None

            # Position status every 5 ticks
            if bot_position and tick_count % 5 == 0:
                pos = bot_position
                if pos["side"] == "LONG":
                    upnl = (price - pos["entry"]) * pos["size"]
                else:
                    upnl = (pos["entry"] - price) * pos["size"]
                bot_trades_log.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "msg": f"POS {pos['side']} @ ${pos['entry']:,.2f} -> ${price:,.2f} | UPnL=${upnl:.2f}",
                    "pnl": round(upnl, 2),
                })

            # Keep last 50 logs
            if len(bot_trades_log) > 50:
                bot_trades_log[:] = bot_trades_log[-50:]

        except Exception as e:
            logger.error(f"Bot tick error: {e}")
            bot_trades_log.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": f"Error: {str(e)[:80]}", "pnl": 0})

        await asyncio.sleep(1)

    logger.info("_bot_trade_loop STOPPED")
    bot_trades_log.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": "Bot stopped", "pnl": 0})



@app.get("/api/market/live")
async def get_market_live():
    """Real-time market data from WebSocket engine (BB + ticker built-in)"""
    try:
        analysis = bws.get_analysis()
        pair = _config_store.get("pair", "BTCUSDT")
        return {
            "pair": pair,
            "price": bws.price,
            "connected": bws.connected,
            "last_tick": bws.last_tick,
            "m1": analysis.get("m1", {}),
            "m5": analysis.get("m5", {}),
            "trade_signal": analysis.get("trade_signal", "NEUTRAL"),
            "aligned": analysis.get("aligned", False),
            "timestamp": analysis.get("timestamp", ""),
            "bb": analysis.get("bb", {}),
            "ticker": analysis.get("ticker", {})
        }
    except Exception as e:
        logger.error(f"market/live: {e}")
        return {"pair": "BTCUSDT", "price": 0, "connected": False, "error": str(e), "bb": {}, "ticker": {}}

@app.get("/api/config-public")
async def get_config_public():
    """Get API config - no auth"""
    return _config_store

@app.post("/api/config-public")
async def save_config_public(body: dict):
    """Save ALL config - no auth"""
    global _config_store, _bot_config_cache
    for k in ["api_key","api_secret","api_passphrase"]:
        if k in body:
            _config_store[k] = body[k]
    if "m1" in body:
        _config_store["m1"] = body["m1"]
    if "m5" in body:
        _config_store["m5"] = body["m5"]
    for k in ["order_size","tp_percent","sl_percent","mode","balance_type","pair","m1_bb_length","m1_bb_std","m1_rsi_length","m1_bb_enabled","m1_macd_enabled","m1_rsi_enabled","m5_bb_length","m5_bb_std","m5_rsi_length","m5_bb_enabled","m5_macd_enabled","m5_rsi_enabled"]:
        if k in body:
            _config_store[k] = body[k]
    _bot_config_cache = {"m1": _config_store["m1"], "m5": _config_store["m5"]}
    try:
        bws.update_params(
            _config_store["m1"].get("fast",4), _config_store["m1"].get("slow",5), _config_store["m1"].get("signal",3),
            _config_store["m5"].get("fast",4), _config_store["m5"].get("slow",5), _config_store["m5"].get("signal",3),
            m1_source=_config_store["m1"].get("source"), m5_source=_config_store["m5"].get("source"))
    except Exception as e:
        logger.error(f"bws.update_params: {e}")
    # Sync pair to WebSocket engine
    if "pair" in body:
        try:
            await bws.update_pair(body["pair"])
        except Exception as e:
            logger.error(f"bws.update_pair: {e}")
    return {"ok": True, "msg": "All Config Saved Securely"}

@app.post("/api/bot/config-public")
async def update_config_public(body: dict):
    return await save_config_public(body)
    """Update MACD config - no auth required"""
    global _bot_config_cache
    _bot_config_cache = {"m1": body.get("m1", {}), "m5": body.get("m5", {})}
    bws.update_params(
        body.get("m1", {}).get("fast", 4), body.get("m1", {}).get("slow", 5), body.get("m1", {}).get("signal", 3),
        body.get("m5", {}).get("fast", 4), body.get("m5", {}).get("slow", 5), body.get("m5", {}).get("signal", 3),
        m1_source=body.get("m1", {}).get("source"), m5_source=body.get("m5", {}).get("source")
    )
    return {"ok": True, "msg": f"Config updated M1({body.get('m1',{}).get('fast',4)}-{body.get('m1',{}).get('slow',5)}-{body.get('m1',{}).get('signal',3)}) M5({body.get('m5',{}).get('fast',4)}-{body.get('m5',{}).get('slow',5)}-{body.get('m5',{}).get('signal',3)})"}

@app.post("/api/bot/start-public")
async def start_bot_public():
    """Start bot - no auth required"""
    global bot_running, bot_trades_log, bot_position, bot_analysis, bot_realized_pnl
    if bot_running:
        return {"ok": True, "status": "already_running", "msg": "Bot already running"}
    bot_running = True
    bot_trades_log = []
    bot_position = None
    bot_realized_pnl = 0.0
    bot_analysis = {"m1": {}, "m5": {}, "aligned": False, "trade_signal": "NEUTRAL"}
    logger.info("Bot started - creating trade loop task")
    asyncio.create_task(_bot_trade_loop())
    # BB+ticker now in WebSocket engine (1s update)
    return {"ok": True, "status": "started", "msg": "Bot started - auto trading"}

@app.post("/api/bot/stop-public")
async def stop_bot_public():
    """Stop bot - no auth required"""
    global bot_running
    bot_running = False
    logger.info("Bot stop requested")
    return {"ok": True, "status": "stopped", "msg": "Bot stopped"}

# ===== DASHBOARD (HTML) =====
@app.get("/dashboard")
async def dashboard():
    return FileResponse(os.path.join(ROOT, "dashboard.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
