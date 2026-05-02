from pydantic import BaseModel


class BotConfigRequest(BaseModel):
    market_mode: str = "spot"
    symbol: str = "BTCUSDT"
    order_size: float = 50
    tp_percent: float = 2.5
    sl_percent: float = 1.5
    leverage: int = 3
    macd_fast: int = 4
    macd_slow: int = 5
    macd_signal: int = 1


class ApiConfigRequest(BaseModel):
    api_key: str = ""
    api_secret: str = ""
    api_passphrase: str = ""
    demo: bool = True
