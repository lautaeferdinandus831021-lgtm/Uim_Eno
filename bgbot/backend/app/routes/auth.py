from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.models.user import User
from app.models.config import ApiConfig, BotConfig
from shared.config import settings
import time, logging, traceback

logger = logging.getLogger("bgbot.auth")
router = APIRouter(tags=["Auth"])
security = HTTPBearer(auto_error=False)


@router.post("/auth/register")
async def register(body: dict, db: AsyncSession = Depends(get_db)):
    email = (body.get("email") or "").lower().strip()
    password = body.get("password") or ""
    confirm = body.get("confirm") or ""
    name = body.get("name") or ""

    if not email or not password:
        raise HTTPException(400, "Email and password required")
    if password != confirm:
        raise HTTPException(400, "Passwords do not match")

    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")

    user = User(email=email, name=name, provider="email", password_hash=hash_password(password))
    db.add(user)
    await db.flush()
    db.add(ApiConfig(user_id=user.id, demo=True))
    db.add(BotConfig(user_id=user.id, config_json=settings.DEFAULT_BOT_CONFIG))
    await db.commit()
    return {"ok": True, "user_id": user.id}


@router.post("/auth/login")
async def login(body: dict, db: AsyncSession = Depends(get_db)):
    try:
        email = (body.get("email") or "").lower().strip()
        password = body.get("password") or ""

        if not email or not password:
            raise HTTPException(400, "Email and password required")

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(401, "Account not found")

        # Debug: show hash info
        stored = user.password_hash
        logger.info(f"Login attempt: email={email}, stored_hash={stored[:30]}...")

        is_valid = verify_password(password, stored)
        logger.info(f"Password valid: {is_valid}")

        if not is_valid:
            raise HTTPException(401, "Wrong password")

        access_token = create_access_token(user.id, user.email)
        user.last_login = time.time()
        await db.commit()

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {"id": user.id, "email": user.email, "name": user.name},
        }
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Login error: {e}\n{tb}")
        raise HTTPException(500, f"Login error: {str(e)}")


@router.get("/auth/me")
async def get_me(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    if not credentials:
        raise HTTPException(401, "Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid token")
    result = await db.execute(select(User).where(User.id == payload["uid"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "User not found")
    return {"id": user.id, "email": user.email, "name": user.name}
