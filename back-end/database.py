import os
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

postgres_user = quote_plus(os.getenv("POSTGRES_USER", "postgres"))
postgres_password = quote_plus(os.getenv("POSTGRES_PASSWORD", "postgres"))
postgres_host = os.getenv("POSTGRES_HOST", "db")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "financas")

URL = (
    f"postgresql+psycopg://{postgres_user}:{postgres_password}"
    f"@{postgres_host}:{postgres_port}/{postgres_db}"
)

engine = create_async_engine(URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session