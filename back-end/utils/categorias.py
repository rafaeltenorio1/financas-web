import uuid

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.categoria import Categoria
from models.usuario import Usuario

CATEGORIA_INVALIDA = HTTPException(status_code=422, detail="Categoria inválida.")

PASTEIS = ["#7dbde8", "#f0a27a", "#a996ee", "#62c4b8", "#ddc170", "#ec93b8"]


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


async def cor_menos_usada(db: AsyncSession, usuario: Usuario) -> str:
    uso = dict(
        (
            await db.execute(
                select(Categoria.cor, func.count())
                .where(Categoria.id_usuario == usuario.id_usuario, Categoria.cor.in_(PASTEIS))
                .group_by(Categoria.cor)
            )
        ).all()
    )
    return min(PASTEIS, key=lambda cor: uso.get(cor, 0))
