from sqlalchemy import create_engine

DB_URL = "sqlite:///./bot.db"

engine = create_engine(
    DB_URL,
    echo=False,  # 🔥 INI KUNCI FIX
    future=True
)
