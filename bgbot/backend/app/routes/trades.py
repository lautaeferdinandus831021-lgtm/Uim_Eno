from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services import trade_service

router = APIRouter(prefix="/api", tags=["Trades"])


@router.get("/trades")
async def get_trades(limit: int = Query(100, le=1000), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await trade_service.get_trades(db, user.id, limit)


@router.get("/trade-stats")
async def get_trade_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await trade_service.get_trade_stats(db, user.id)


@router.get("/positions")
async def get_positions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await trade_service.get_positions(db, user.id)


@router.get("/export-trades")
async def export_trades(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    csv_data = await trade_service.export_csv(db, user.id)
    return StreamingResponse(iter([csv_data]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=bgbot_{user.id}.csv"})
