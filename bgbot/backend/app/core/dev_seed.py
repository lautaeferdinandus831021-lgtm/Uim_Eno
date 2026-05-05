import logging
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.config import ApiConfig, BotConfig
from shared.config import settings

logger = logging.getLogger("bgbot.devseed")

DEV_EMAIL = "dev@bgbot.local"


async def seed_dev_user():
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(User).where(User.email == DEV_EMAIL))
            user = result.scalar_one_or_none()
            if not user:
                user = User(email=DEV_EMAIL, name="Dev User", provider="dev", password_hash=hash_password("dev123456"))
                db.add(user)
                await db.flush()
                db.add(ApiConfig(user_id=user.id, demo=True))
                db.add(BotConfig(user_id=user.id, config_json=settings.DEFAULT_BOT_CONFIG))
                await db.commit()
                logger.info("Dev user created")
        except Exception as e:
            logger.warning(f"Seed: {e}")
            await db.rollback()
