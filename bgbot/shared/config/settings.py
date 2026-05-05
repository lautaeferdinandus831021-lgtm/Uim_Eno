from pydantic_settings import BaseSettings
from typing import Dict, Any

class Settings(BaseSettings):
    DEBUG: bool = True

    JWT_ACCESS_EXPIRY: int = 900
    JWT_REFRESH_EXPIRY: int = 604800
    ENCRYPT_KEY: str = ""

    DATABASE_URL: str = "sqlite+aiosqlite:///./bgbot.db"

    REDIS_URL: str = "redis://localhost:6379/0"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = "noreply@bgbot.io"

    MAX_REQUESTS_PER_MINUTE: int = 60
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_SECONDS: int = 900
    MAX_SESSIONS_PER_USER: int = 10
    SESSION_LIFETIME: int = 86400

    FRONTEND_URL: str = "http://localhost:3000"
    DEFAULT_EXCHANGE: str = "bitget"

    DEFAULT_BOT_CONFIG: Dict[str, Any] = {
        "market_mode": "spot",
        "symbol": "BTCUSDT",
        "order_size": 50,
        "max_positions": 3,
        "tp_percent": 2.5,
        "sl_percent": 1.5,
        "leverage": 3,
        "margin_mode": "crossed",
        "order_type": "market",
        "limit_offset": 0.2,
        "strategy": "macd_451",
        "macd_fast": 4,
        "macd_slow": 5,
        "macd_signal": 1,
        "risk_pct": 1.0,
        "cooldown_seconds": 60,
        "use_balance_pct": False,
        "max_daily_loss_pct": 5.0,
        "max_trades_per_hour": 10,
    }

settings = Settings()
