import uuid

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.categoria import Categoria
from models.usuario import Usuario

CATEGORIA_INVALIDA = HTTPException(status_code=422, detail="Categoria inválida.")


async def validar_categoria(
    db: AsyncSession, id_categoria: uuid.UUID | None, usuario: Usuario
) -> None:
    if id_categoria is None:
        return
    permitida = await db.scalar(
        select(Categoria.id_categoria).where(
            Categoria.id_categoria == id_categoria,
            or_(
                Categoria.id_usuario.is_(None),
                Categoria.id_usuario == usuario.id_usuario,
            ),
        )
    )
    if permitida is None:
        raise CATEGORIA_INVALIDA
