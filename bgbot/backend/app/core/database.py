import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DB_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./bgbot.db")

# Fix URL for sqlite
if DB_URL.startswith("sqlite"):
    engine = create_async_engine(DB_URL, echo=False)
else:
    # Fallback to sqlite if postgres not available
    DB_URL = "sqlite+aiosqlite:///./bgbot.db"
    engine = create_async_engine(DB_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
