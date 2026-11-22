from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

FUSO_INVALIDO = HTTPException(status_code=422, detail="Fuso horário inválido.")


async def validar_fuso(db: AsyncSession, fuso: str) -> None:
    existe = await db.scalar(
        text("SELECT 1 FROM pg_timezone_names WHERE name = :fuso"), {"fuso": fuso}
    )
    if existe is None:
        raise FUSO_INVALIDO
