import pytest

def test_password_hashing():
    from backend.app.core.security import hash_password, verify_password
    pw = "test123456"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed)
    assert not verify_password("wrong", hashed)

def test_jwt_token():
    from backend.app.core.security import create_access_token, decode_token
    token = create_access_token(1, "test@test.com")
    payload = decode_token(token)
    assert payload is not None
    assert payload["uid"] == 1
    assert payload["email"] == "test@test.com"
    assert payload["type"] == "access"

def test_jwt_refresh():
    from backend.app.core.security import create_refresh_token, decode_token
    token = create_refresh_token(1)
    payload = decode_token(token)
    assert payload["type"] == "refresh"

def test_invalid_token():
    from backend.app.core.security import decode_token
    assert decode_token("invalid") is None
    assert decode_token("") is None

def test_generate_token():
    from backend.app.core.security import generate_token
    t1, t2 = generate_token(), generate_token()
    assert t1 != t2
    assert len(t1) > 20

def test_encryption():
    from shared.utils.encryption import encrypt, decrypt
    val = "my-secret-api-key"
    assert decrypt(encrypt(val)) == val

def test_macd_indicator():
    import pandas as pd, numpy as np
    from domain.trading.indicators import MACD
    np.random.seed(42)
    df = pd.DataFrame({"close": 100 + np.cumsum(np.random.randn(100) * 0.5), "timestamp": pd.date_range("2024-01-01", periods=100, freq="1min")})
    macd = MACD(fast=4, slow=5, signal=1)
    signal, overlays = macd.compute(df)
    assert signal in ("LONG", "SHORT", "NEUTRAL")
    assert overlays is not None
    assert "macd_line" in overlays

def test_macd_fast():
    import pandas as pd, numpy as np
    from domain.trading.indicators import MACD
    np.random.seed(42)
    df = pd.DataFrame({"close": 100 + np.cumsum(np.random.randn(100) * 0.5)})
    assert MACD().compute_fast(df) in ("LONG", "SHORT", "NEUTRAL")

def test_macd_short_data():
    import pandas as pd
    from domain.trading.indicators import MACD
    df = pd.DataFrame({"close": [100, 101]})
    signal, overlays = MACD().compute(df)
    assert signal == "NEUTRAL"
    assert overlays is None

def test_ema():
    import pandas as pd
    from domain.trading.indicators import EMA
    series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert len(EMA(3).compute(series)) == 10
    assert EMA(3).compute_last(series) > 0

def test_rsi():
    import pandas as pd, numpy as np
    from domain.trading.indicators import RSI
    np.random.seed(42)
    df = pd.DataFrame({"close": 100 + np.cumsum(np.random.randn(50) * 0.5)})
    val = RSI(14).compute_last(df)
    assert 0 <= val <= 100

def test_risk_manager():
    from domain.trading.risk import RiskManager
    cfg = {"max_daily_loss_pct": 5.0, "max_trades_per_hour": 3, "risk_pct": 2.0}
    rm = RiskManager(cfg)
    assert rm.check_daily_loss(1000) is True
    assert rm.check_trade_limit() is True
    rm.record_trade(-40)
    assert rm.check_daily_loss(1000) is False

def test_risk_position_size():
    from domain.trading.risk import RiskManager
    rm = RiskManager({"risk_pct": 2.0})
    assert rm.check_position_size(50, 10000) == 50
    assert rm.check_position_size(500, 10000) == 200

def test_risk_status():
    from domain.trading.risk import RiskManager
    rm = RiskManager({"max_daily_loss_pct": 5.0, "max_trades_per_hour": 10})
    rm.record_trade(-10)
    status = rm.get_status(1000)
    assert status["daily_loss"] == 10
    assert status["can_trade"] is True

def test_backtest_metrics():
    from domain.backtest.metrics import BacktestMetrics
    trades = [{"pnl": 10, "pnl_pct": 2, "fee": 0.1}, {"pnl": -5, "pnl_pct": -1, "fee": 0.1}, {"pnl": 8, "pnl_pct": 1.5, "fee": 0.1}]
    m = BacktestMetrics.calculate(10000, 10013, trades, 5, 0.05)
    assert m["total_trades"] == 3
    assert m["wins"] == 2
    assert m["win_rate"] == 66.7

def test_backtest_engine():
    import pandas as pd, numpy as np
    from domain.backtest import BacktestEngine
    np.random.seed(42)
    prices = 68000 + np.cumsum(np.random.randn(100) * 50)
    df = pd.DataFrame({"close": prices, "open": prices - 10, "high": prices + 20, "low": prices - 20, "volume": np.random.rand(100) * 100, "timestamp": pd.date_range("2024-01-01", periods=100, freq="5min")})
    result = BacktestEngine({"macd_fast": 4, "macd_slow": 5, "macd_signal": 1, "order_size": 50, "tp_percent": 2.5, "sl_percent": 1.5}).run(df, 10000)
    assert "metrics" in result
    assert result["metrics"]["initial_balance"] == 10000

def test_backtest_insufficient():
    import pandas as pd
    from domain.backtest import BacktestEngine
    df = pd.DataFrame({"close": [100, 101, 102], "open": [99, 100, 101], "high": [101, 102, 103], "low": [99, 100, 101], "volume": [10, 10, 10], "timestamp": pd.date_range("2024-01-01", periods=3, freq="5min")})
    assert "error" in BacktestEngine({}).run(df)

def test_strategy_should_execute():
    from domain.trading.strategies import MACD451Strategy
    cfg = {"macd_fast": 4, "macd_slow": 5, "macd_signal": 1, "max_daily_loss_pct": 5.0, "max_trades_per_hour": 10}
    s = MACD451Strategy(cfg)
    assert s.should_execute("LONG", "LONG", "NEUTRAL", 10000, False)[0] is True
    assert s.should_execute("LONG", "SHORT", "NEUTRAL", 10000, False)[0] is False
    assert s.should_execute("LONG", "LONG", "LONG", 10000, False)[0] is False
    assert s.should_execute("LONG", "LONG", "NEUTRAL", 10000, True)[0] is False

def test_strategy_tp_sl():
    from domain.trading.strategies import MACD451Strategy
    s = MACD451Strategy({"macd_fast": 4, "macd_slow": 5, "macd_signal": 1, "tp_percent": 2.5, "sl_percent": 1.5, "max_daily_loss_pct": 5.0, "max_trades_per_hour": 10})
    tp, sl = s.calculate_tp_sl(100, "LONG")
    assert tp == 102.5 and sl == 98.5
    tp, sl = s.calculate_tp_sl(100, "SHORT")
    assert tp == 97.5 and sl == 101.5

def test_event_types():
    from shared.events.types import Event, EventType
    e = Event(type=EventType.BOT_STARTED, user_id=1, data={"mode": "spot"})
    d = e.to_dict()
    assert d["type"] == "bot.started"
    e2 = Event.from_dict(d)
    assert e2.type == EventType.BOT_STARTED

def test_sim_data():
    from shared.utils.helpers import SimData
    df = SimData.gen("BTCUSDT", 50, 1)
    assert len(df) == 50
    assert "close" in df.columns

def test_settings():
    from shared.config import settings
    assert settings.APP_NAME == "BG-BOT v5"
    assert settings.DEFAULT_BOT_CONFIG["macd_fast"] == 4
