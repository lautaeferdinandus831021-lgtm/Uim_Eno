import io, csv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.trade import Trade, Position


async def get_trades(db, user_id, limit=100):
    result = await db.execute(select(Trade).where(Trade.user_id == user_id).order_by(Trade.id.desc()).limit(limit))
    return [{"id": t.id, "trade_time": str(t.trade_time) if t.trade_time else "", "mode": t.mode, "side": t.side, "pair": t.pair, "price": t.price, "order_type": t.order_type, "size": t.size, "pnl": t.pnl, "pnl_pct": t.pnl_pct, "fee": t.fee, "status": t.status, "order_id": t.order_id} for t in result.scalars().all()]


async def get_trade_stats(db, user_id):
    total = (await db.execute(select(func.count(Trade.id)).where(Trade.user_id == user_id))).scalar()
    wins = (await db.execute(select(func.count(Trade.id)).where(Trade.user_id == user_id, Trade.pnl > 0))).scalar()
    losses = (await db.execute(select(func.count(Trade.id)).where(Trade.user_id == user_id, Trade.pnl <= 0))).scalar()
    pnl = (await db.execute(select(func.coalesce(func.sum(Trade.pnl), 0)).where(Trade.user_id == user_id))).scalar()
    spot = (await db.execute(select(func.count(Trade.id)).where(Trade.user_id == user_id, Trade.mode == "spot"))).scalar()
    perp = (await db.execute(select(func.count(Trade.id)).where(Trade.user_id == user_id, Trade.mode == "perp"))).scalar()
    return {"total": total, "wins": wins, "losses": losses, "total_pnl": round(float(pnl), 2), "spot": spot, "perp": perp, "win_rate": round(wins / total * 100, 1) if total > 0 else 0}


async def get_positions(db, user_id):
    result = await db.execute(select(Position).where(Position.user_id == user_id))
    return [{"id": p.id, "symbol": p.symbol, "side": p.side, "size": p.size, "entry_price": p.entry_price, "current_price": p.current_price, "pnl": p.pnl, "pnl_pct": p.pnl_pct, "hold_side": p.hold_side, "leverage": p.leverage} for p in result.scalars().all()]


async def export_csv(db, user_id):
    result = await db.execute(select(Trade).where(Trade.user_id == user_id).order_by(Trade.id.desc()).limit(10000))
    trades = result.scalars().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Time", "Mode", "Side", "Pair", "Price", "Type", "Size", "PnL", "PnL%", "Fee", "Status", "OrderID"])
    for t in trades:
        writer.writerow([t.trade_time, t.mode, t.side, t.pair, t.price, t.order_type, t.size, t.pnl, t.pnl_pct, t.fee, t.status, t.order_id])
    output.seek(0)
    return output.getvalue()
