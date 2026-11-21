import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.categoria import Categoria
from models.enums import TipoTransacao
from models.usuario import Usuario
from schemas.categoria import CategoriaCreate, CategoriaOut, CategoriaUpdate
from utils.auth import get_usuario_atual
from utils.csrf import verificar_csrf, verificar_origem

router = APIRouter(
    prefix="/categorias",
    tags=["categorias"],
    dependencies=[Depends(verificar_origem), Depends(verificar_csrf)],
)

NAO_ENCONTRADA = HTTPException(status_code=404, detail="Categoria não encontrada.")
PADRAO_SO_LEITURA = HTTPException(
    status_code=403, detail="Categorias padrão não podem ser alteradas."
)
NOME_EM_USO = HTTPException(status_code=409, detail="Já existe uma categoria com esse nome.")


def _visivel_para(usuario: Usuario):

    return or_(Categoria.id_usuario.is_(None), Categoria.id_usuario == usuario.id_usuario)


async def _buscar_categoria_propria(
    db: AsyncSession, id_categoria: uuid.UUID, usuario: Usuario
) -> Categoria:
    categoria = await db.scalar(
        select(Categoria).where(
            Categoria.id_categoria == id_categoria, _visivel_para(usuario)
        )
    )

    if categoria is None:
        raise NAO_ENCONTRADA

    if categoria.padrao:
        raise PADRAO_SO_LEITURA
    return categoria


async def _nome_em_uso(
    db: AsyncSession, nome: str, usuario: Usuario, ignorar: uuid.UUID | None = None
) -> bool:

    consulta = select(Categoria.id_categoria).where(
        func.lower(Categoria.nome) == func.lower(nome), _visivel_para(usuario)
    )
    if ignorar is not None:
        consulta = consulta.where(Categoria.id_categoria != ignorar)
    return await db.scalar(consulta.limit(1)) is not None


async def _salvar(db: AsyncSession, categoria: Categoria) -> Categoria:

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise NOME_EM_USO
    await db.refresh(categoria)
    return categoria


@router.get("", response_model=list[CategoriaOut])
async def listar_categorias(
    tipo: TipoTransacao | None = Query(default=None),
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    consulta = select(Categoria).where(_visivel_para(usuario))
    if tipo is not None:
        # Sem tipo_padrao a categoria serve para os dois tipos, então entra no filtro.
        consulta = consulta.where(
            or_(Categoria.tipo_padrao == tipo, Categoria.tipo_padrao.is_(None))
        )
    resultado = await db.scalars(consulta.order_by(Categoria.nome))
    return resultado.all()


@router.post("", status_code=201, response_model=CategoriaOut)
async def criar_categoria(
    dados: CategoriaCreate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    if await _nome_em_uso(db, dados.nome, usuario):
        raise NOME_EM_USO

    nova = Categoria(**dados.model_dump(), id_usuario=usuario.id_usuario)
    db.add(nova)
    return await _salvar(db, nova)


@router.patch("/{id_categoria}", response_model=CategoriaOut)
async def editar_categoria(
    id_categoria: uuid.UUID,
    dados: CategoriaUpdate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    categoria = await _buscar_categoria_propria(db, id_categoria, usuario)

    alteracoes = dados.model_dump(exclude_unset=True)
    if "nome" in alteracoes and await _nome_em_uso(
        db, alteracoes["nome"], usuario, ignorar=categoria.id_categoria
    ):
        raise NOME_EM_USO

    for campo, valor in alteracoes.items():
        setattr(categoria, campo, valor)
    return await _salvar(db, categoria)


@router.delete("/{id_categoria}", status_code=204)
async def apagar_categoria(
    id_categoria: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    categoria = await _buscar_categoria_propria(db, id_categoria, usuario)

    await db.delete(categoria)
    await db.commit()
    return Response(status_code=204)
