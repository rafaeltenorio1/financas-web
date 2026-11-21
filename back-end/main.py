from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from routers import categorias
from routers import auth
from utils.config import settings

app = FastAPI(title="Finanças", version="0.1.0")


@app.get("/saude")
async def saude(db: AsyncSession = Depends(get_db)):
    # Usa a mesma conexão das rotas, então também valida a configuração do database.py.
    resultado = await db.scalar(text("SELECT 1"))
    return {"api": "ok", "banco": resultado == 1}


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

app.include_router(categorias.router)
app.include_router(auth.router)
