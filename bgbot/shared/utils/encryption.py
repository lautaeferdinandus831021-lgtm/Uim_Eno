from cryptography.fernet import Fernet
from shared.config import settings
import logging

logger = logging.getLogger("bgbot.crypto")
_fernet = None

if settings.ENCRYPT_KEY:
    try:
        _fernet = Fernet(settings.ENCRYPT_KEY.encode() if len(settings.ENCRYPT_KEY) == 44 else Fernet.generate_key())
    except Exception as e:
        logger.warning(f"Encryption init: {e}")


def encrypt(val: str) -> str:
    if not val:
        return ""
    if _fernet:
        try:
            return _fernet.encrypt(val.encode()).decode()
        except Exception:
            pass
    return val


def decrypt(val: str) -> str:
    if not val:
        return ""
    if _fernet:
        try:
            return _fernet.decrypt(val.encode()).decode()
        except Exception:
            pass
    return val


def is_enabled() -> bool:
    return _fernet is not None
