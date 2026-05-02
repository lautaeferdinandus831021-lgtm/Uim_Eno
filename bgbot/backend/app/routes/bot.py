from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services import bot_service

router = APIRouter(prefix="/api", tags=["Bot"])


@router.get("/get-config")
async def get_config(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await bot_service.get_config(db, user.id)


@router.post("/save-config")
async def save_config(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await bot_service.save_config(db, user.id, body)


@router.post("/save-api")
async def save_api(body: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await bot_service.save_api_config(db, user.id, body)


@router.get("/test-api")
async def test_api(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await bot_service.test_api(db, user.id)


@router.post("/bot/start")
async def start_bot(user: User = Depends(get_current_user)):
    return await bot_service.start_bot(user.id)


@router.post("/bot/stop")
async def stop_bot(user: User = Depends(get_current_user)):
    return await bot_service.stop_bot(user.id)
