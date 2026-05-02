from pydantic import BaseModel
from typing import Optional, Dict, Any


class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    granularity: str = "5m"
    days: int = 7
    initial_balance: float = 10000
    config: Optional[Dict[str, Any]] = None
