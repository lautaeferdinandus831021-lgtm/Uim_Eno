import time
import secrets
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from shared.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(uid: int, email: str) -> str:
    return jwt.encode({"uid": uid, "email": email, "type": "access", "exp": int(time.time()) + settings.JWT_ACCESS_EXPIRY, "iat": int(time.time()), "jti": secrets.token_hex(8)}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(uid: int) -> str:
    return jwt.encode({"uid": uid, "type": "refresh", "exp": int(time.time()) + settings.JWT_REFRESH_EXPIRY, "iat": int(time.time()), "jti": secrets.token_hex(16)}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def generate_token(length=32) -> str:
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()
