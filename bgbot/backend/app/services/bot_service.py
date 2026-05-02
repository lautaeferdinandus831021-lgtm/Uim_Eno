import json, logging, asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.config import ApiConfig, BotConfig
from app.core.redis import redis_client
from shared.config import settings
from shared.utils.encryption import encrypt as enc, decrypt as dec

logger = logging.getLogger("bgbot.bot_svc")


async def get_config(db, user_id):
    result = await db.execute(select(BotConfig).where(BotConfig.user_id == user_id))
    cfg = result.scalar_one_or_none()
    if cfg and cfg.config_json: return cfg.config_json
    return settings.DEFAULT_BOT_CONFIG


async def save_config(db, user_id, data):
    result = await db.execute(select(BotConfig).where(BotConfig.user_id == user_id))
    cfg = result.scalar_one_or_none()
    if cfg: cfg.config_json = data
    else: db.add(BotConfig(user_id=user_id, config_json=data))
    await db.flush()
    await redis_client.publish(f"user:{user_id}:config", json.dumps(data))
    return {"ok": True}


async def get_api_config(db, user_id):
    result = await db.execute(select(ApiConfig).where(ApiConfig.user_id == user_id))
    api = result.scalar_one_or_none()
    if api: return {"api_key": dec(api.api_key or ""), "api_secret": dec(api.api_secret or ""), "api_passphrase": dec(api.api_passphrase or ""), "demo": bool(api.demo)}
    return {"api_key": "", "api_secret": "", "api_passphrase": "", "demo": True}


async def save_api_config(db, user_id, data):
    result = await db.execute(select(ApiConfig).where(ApiConfig.user_id == user_id))
    api = result.scalar_one_or_none()
    if api:
        api.api_key = enc(data.get("api_key", ""))
        api.api_secret = enc(data.get("api_secret", ""))
        api.api_passphrase = enc(data.get("api_passphrase", ""))
        api.demo = data.get("demo", True)
    else:
        db.add(ApiConfig(user_id=user_id, api_key=enc(data.get("api_key", "")), api_secret=enc(data.get("api_secret", "")), api_passphrase=enc(data.get("api_passphrase", "")), demo=data.get("demo", True)))
    await db.flush()
    return {"ok": True}


async def test_api(db, user_id):
    api = await get_api_config(db, user_id)
    if not api.get("api_key"): return {"ok": False, "msg": "No API configured"}
    try:
        from gateway import get_exchange
        client = get_exchange("bitget", api["api_key"], api["api_secret"], api["api_passphrase"], api.get("demo", True))
        result = await asyncio.to_thread(client.test)
        return result
    except Exception as e:
        return {"ok": False, "msg": str(e)}


async def start_bot(user_id):
    await redis_client.publish(f"user:{user_id}:control", json.dumps({"action": "start"}))
    return {"ok": True, "msg": "Bot starting"}


async def stop_bot(user_id):
    await redis_client.publish(f"user:{user_id}:control", json.dumps({"action": "stop"}))
    return {"ok": True, "msg": "Bot stopping"}
