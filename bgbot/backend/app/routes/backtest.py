from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.backtest import BacktestRequest
from app.services import backtest_service

router = APIRouter(prefix="/api", tags=["Backtest"])


@router.post("/run-backtest")
async def run_backtest(body: BacktestRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await backtest_service.run_backtest(db, user.id, body.symbol, body.granularity, body.days, body.initial_balance, body.config)
    if "error" in result: raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/backtest-history")
async def backtest_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await backtest_service.get_history(db, user.id)
