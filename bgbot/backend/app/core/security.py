import hashlib, secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from shared.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${pw_hash}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt, pw_hash = hashed.split("$", 1)
        return hashlib.sha256((salt + plain).encode()).hexdigest() == pw_hash
    except Exception:
        return False


def create_access_token(uid: int, email: str, expires_delta=None):
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    return jwt.encode({"uid": uid, "email": email, "type": "access", "exp": expire}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(uid: int):
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    return jwt.encode({"uid": uid, "type": "refresh", "exp": expire}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str):
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def generate_token(length=32):
    return secrets.token_urlsafe(length)


def hash_token(token: str):
    return hashlib.sha256(token.encode()).hexdigest()
