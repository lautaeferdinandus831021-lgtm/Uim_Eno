from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from shared.config import settings
import time

_store = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_req=None):
        super().__init__(app)
        self.max_req = max_req or settings.MAX_REQUESTS_PER_MINUTE

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/metrics"):
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        now = int(time.time())
        window = now // 60
        key = f"{ip}:{window}"
        _store[key] = _store.get(key, 0) + 1
        if _store[key] > self.max_req:
            raise HTTPException(status_code=429, detail="Too many requests")
        if len(_store) > 10000:
            cutoff = window - 2
            for k in list(_store):
                if int(k.split(":")[1]) < cutoff:
                    del _store[k]
        return await call_next(request)
