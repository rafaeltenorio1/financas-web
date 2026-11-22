import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from routers import categorias
from routers import auth
from routers import transacoes
from routers import contas_recorrentes
from routers import importacoes
from utils.config import settings
from utils.email import aguardar_envios
from utils.lembretes import executar_lembretes_periodicos
from utils.limpeza import executar_limpeza_periodica


@asynccontextmanager
async def lifespan(app: FastAPI):
    tarefas = [
        asyncio.create_task(executar_limpeza_periodica()),
        asyncio.create_task(executar_lembretes_periodicos()),
    ]
    yield
    for tarefa in tarefas:
        tarefa.cancel()
    for tarefa in tarefas:
        with suppress(asyncio.CancelledError):
            await tarefa
    await aguardar_envios(timeout=10)


app = FastAPI(title="Finanças", version="0.1.0", lifespan=lifespan)


@app.get("/saude")
async def saude(db: AsyncSession = Depends(get_db)):
    resultado = await db.scalar(text("SELECT 1"))
    return {"api": "ok", "banco": resultado == 1}


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
    expose_headers=["Content-Disposition"],
)

app.include_router(categorias.router)
app.include_router(auth.router)
app.include_router(transacoes.router)
app.include_router(contas_recorrentes.router)
app.include_router(importacoes.router)
