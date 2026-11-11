from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.categoria import Categoria
from schemas.categoria import CategoriaOut

router = APIRouter(prefix="/categorias", tags=["categorias"])

@router.get("", response_model=list[CategoriaOut])
async def get_categorias(db: AsyncSession = Depends(get_db)):

    query = select(Categoria).order_by(Categoria.nome).where(Categoria.id_usuario.is_(None))
    result = await db.scalars(query)
    return result.all()