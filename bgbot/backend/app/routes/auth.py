from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest, ForgotRequest, ResetRequest, RefreshRequest
from app.services import auth_service
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
async def route_login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    data, err = await auth_service.login(db, body.email, body.password, body.otp, request)
    if err: raise HTTPException(status_code=400, detail=err)
    return data


@router.post("/register")
async def route_register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user, err = await auth_service.register(db, body.email, body.password, body.confirm)
    if err: raise HTTPException(status_code=400, detail=err)
    return {"ok": True, "user_id": user.id}


@router.post("/forgot")
async def route_forgot(body: ForgotRequest, db: AsyncSession = Depends(get_db)):
    data, err = await auth_service.forgot_password(db, body.email)
    if err: raise HTTPException(status_code=400, detail=err)
    return data


@router.post("/reset")
async def route_reset(body: ResetRequest, db: AsyncSession = Depends(get_db)):
    data, err = await auth_service.reset_password(db, body.token, body.password, body.confirm)
    if err: raise HTTPException(status_code=400, detail=err)
    return data


@router.post("/refresh")
async def route_refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    data, err = await auth_service.refresh_access(db, body.refresh_token)
    if err: raise HTTPException(status_code=401, detail=err)
    return data


@router.get("/me")
async def route_me(user: User = Depends(get_current_user)):
    return await auth_service.get_me(user)
