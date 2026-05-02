import os


class WorkerSettings:
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://bgbot:bgbot_secret@localhost:5432/bgbt")
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    ENCRYPT_KEY = os.environ.get("ENCRYPT_KEY", "")
    DEFAULT_BOT_CONFIG = {"market_mode": "spot", "symbol": "BTCUSDT", "order_size": 50, "max_positions": 3, "tp_percent": 2.5, "sl_percent": 1.5, "leverage": 3, "margin_mode": "crossed", "order_type": "market", "limit_offset": 0.2, "macd_fast": 4, "macd_slow": 5, "macd_signal": 1, "risk_pct": 1.0, "cooldown_seconds": 60, "use_balance_pct": False, "max_daily_loss_pct": 5.0, "max_trades_per_hour": 10}


worker_settings = WorkerSettings()
