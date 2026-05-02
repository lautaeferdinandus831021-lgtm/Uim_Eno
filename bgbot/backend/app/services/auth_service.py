import time, logging, hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.session import Session, RefreshToken, SecurityLog
from app.models.config import ApiConfig, BotConfig
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, hash_token, generate_token
from shared.config import settings

logger = logging.getLogger("bgbot.auth")


async def register(db, email, password, confirm):
    if not email or "@" not in email: return None, "Invalid email"
    if len(password) < 6: return None, "Password must be 6+ chars"
    if password != confirm: return None, "Passwords do not match"
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none(): return None, "Email already registered"
    user = User(email=email.lower(), name=email.split("@")[0], password_hash=hash_password(password), provider="email")
    db.add(user)
    await db.flush()
    db.add(ApiConfig(user_id=user.id))
    db.add(BotConfig(user_id=user.id, config_json=settings.DEFAULT_BOT_CONFIG))
    await db.flush()
    await db.refresh(user)
    logger.info(f"Registered: {email}")
    return user, None


async def login(db, email, password, otp=None, request=None):
    if not email or not password: return None, "Email and password required"
    email = email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user: return None, "Account not found"
    if not user.password_hash: return None, "This account uses Google login"
    if user.locked_until > time.time(): return None, f"Locked. Try in {int(user.locked_until - time.time())}s"
    if user.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
        user.locked_until = time.time() + settings.LOGIN_LOCKOUT_SECONDS
        await db.flush()
        return None, "Too many attempts. Locked."
    if not verify_password(password, user.password_hash):
        user.login_attempts += 1
        await db.flush()
        return None, "Wrong password"
    if user.totp_enabled:
        if not otp: return {"require_otp": True}, None
        try:
            import pyotp
            if not pyotp.TOTP(user.totp_secret).verify(str(otp), valid_window=1):
                return None, "Invalid OTP"
        except ImportError:
            return None, "2FA not available"
        except Exception:
            return None, "OTP error"
    user.login_attempts = 0
    user.locked_until = 0
    user.last_login = time.time()
    session_token = generate_token(32)
    ua = request.headers.get("User-Agent", "")[:200] if request else ""
    ip = request.client.host if request and request.client else "unknown"
    device_id = hashlib.sha256(f"{ua}|{ip}".encode()).hexdigest()
    now = time.time()
    db.add(Session(session_token=session_token, user_id=user.id, device_id=device_id, ip=ip, user_agent=ua, created_at=now, last_used=now, expires_at=now + settings.SESSION_LIFETIME))
    refresh_raw = generate_token(48)
    db.add(RefreshToken(token_hash=hash_token(refresh_raw), user_id=user.id, device_id=device_id, created_at=now, expires_at=now + settings.JWT_REFRESH_EXPIRY))
    db.add(SecurityLog(user_id=user.id, event="login_success", ip=ip, user_agent=ua, created_at=now))
    await db.flush()
    return {"access_token": create_access_token(user.id, user.email), "refresh_token": refresh_raw, "session_token": session_token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "name": user.name, "picture": user.picture, "provider": user.provider, "totp_enabled": user.totp_enabled}}, None


async def refresh_access(db, refresh_token):
    token_hash = hash_token(refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash, RefreshToken.revoked == False))
    rt = result.scalar_one_or_none()
    if not rt: return None, "Invalid refresh token"
    if rt.expires_at < time.time(): return None, "Refresh token expired"
    user_result = await db.execute(select(User).where(User.id == rt.user_id))
    user = user_result.scalar_one_or_none()
    if not user: return None, "User not found"
    return {"access_token": create_access_token(user.id, user.email)}, None


async def forgot_password(db, email):
    if not email: return None, "Enter your email"
    result = await db.execute(select(User).where(User.email == email.strip().lower()))
    user = result.scalar_one_or_none()
    if user:
        token = generate_token(32)
        user.reset_token = token
        user.reset_token_expires = time.time() + 3600
        await db.flush()
        logger.info(f"Reset token: {email}")
    return {"message": "If email exists, link sent"}, None


async def reset_password(db, token, password, confirm):
    if not token: return None, "Invalid reset link"
    result = await db.execute(select(User).where(User.reset_token == token))
    user = result.scalar_one_or_none()
    if not user: return None, "Invalid reset link"
    if user.reset_token_expires < time.time(): return None, "Reset link expired"
    if len(password) < 6: return None, "Password must be 6+ chars"
    if password != confirm: return None, "Passwords do not match"
    user.password_hash = hash_password(password)
    user.reset_token = ""
    user.reset_token_expires = 0
    await db.flush()
    return {"message": "Password reset done"}, None


async def get_me(user):
    return {"id": user.id, "email": user.email, "name": user.name, "picture": user.picture, "provider": user.provider, "totp_enabled": user.totp_enabled}
