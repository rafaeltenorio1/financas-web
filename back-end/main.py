import os 

import psycopg
from fastapi import FastAPI

from routers import categorias

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

app.include_router(categorias.router)