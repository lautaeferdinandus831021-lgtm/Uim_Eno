import json, logging
from worker.app.celery_app import celery_app
from worker.app.config import worker_settings

logger = logging.getLogger("bgbot.worker.backtest")


@celery_app.task(name="worker.app.tasks.backtest_tasks.run_backtest", bind=True)
def run_backtest(self, user_id, config, symbol, granularity, days, initial_balance):
    from domain.backtest import BacktestEngine
    from gateway.bitget import BitgetClient
    logger.info(f"Backtest: {symbol} {granularity} {days}d ${initial_balance}")
    try:
        df = BitgetClient.fetch_historical(symbol, granularity, days)
        if df is None or df.empty: return {"error": "No data"}
        result = BacktestEngine(config).run(df, initial_balance)
        if "error" in result: return result
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        url = worker_settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
        engine = create_engine(url)
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            db.execute(text("INSERT INTO backtest_results (user_id, config_json, metrics_json, trades_json, equity_json) VALUES (:uid, :cfg, :m, :t, :e)"), {"uid": user_id, "cfg": json.dumps(config), "m": json.dumps(result["metrics"]), "t": json.dumps(result["trades"]), "e": json.dumps(result["equity"])})
            db.commit()
        finally: db.close()
        return result
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return {"error": str(e)}
