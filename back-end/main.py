import os 

import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import categorias
from routers import auth
from utils.config import settings

app = FastAPI(title="Finanças", version="0.1.0")

def conectar():
    return psycopg.connect(
        host="db",
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"]
    )

@app.get("/saude")
def saude(): 
    with conectar() as conn:    
        resultado = conn.execute("SELECT 1").fetchone()
    return {"api": "ok", "banco": resultado[0] == 1}


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

app.include_router(categorias.router)
app.include_router(auth.router)
