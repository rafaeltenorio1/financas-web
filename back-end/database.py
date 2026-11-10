import os 

from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

postgres_user = quote_plus(os.getenv("POSTGRES_USER", "postgres"))
postgres_password = quote_plus(os.getenv("POSTGRES_PASSWORD", "postgres"))
postgres_host = os.getenv("POSTGRES_HOST", "db")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "financas")

URL = f"postgresql+psycopg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"

engine = create_engine(URL)
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass