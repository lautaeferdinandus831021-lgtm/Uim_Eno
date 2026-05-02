import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.config import BacktestResult
from shared.config import settings

logger = logging.getLogger("bgbot.backtest_svc")


async def run_backtest(db, user_id, symbol, granularity, days, initial_balance, config):
    from gateway.bitget import BitgetClient
    from domain.backtest import BacktestEngine
    cfg = config or settings.DEFAULT_BOT_CONFIG
    df = BitgetClient.fetch_historical(symbol, granularity, days)
    if df is None or df.empty: return {"error": "Failed to fetch data"}
    result = BacktestEngine(cfg).run(df, initial_balance)
    if "error" in result: return result
    db.add(BacktestResult(user_id=user_id, config_json=cfg, metrics_json=result["metrics"], trades_json=result["trades"], equity_json=result["equity"]))
    await db.flush()
    return result


async def get_history(db, user_id, limit=20):
    result = await db.execute(select(BacktestResult).where(BacktestResult.user_id == user_id).order_by(BacktestResult.id.desc()).limit(limit))
    return [{"id": r.id, "created_at": str(r.created_at), "config": r.config_json, "metrics": r.metrics_json} for r in result.scalars().all()]
