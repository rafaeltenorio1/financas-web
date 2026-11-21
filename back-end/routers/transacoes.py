import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AwareDatetime
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.categoria import Categoria
from models.enums import TipoTransacao
from models.transacao import Transacao
from models.usuario import Usuario
from schemas.transacao import TransacaoCreate, TransacaoOut, TransacaoUpdate
from utils.auth import get_usuario_atual
from utils.csrf import verificar_csrf, verificar_origem

router = APIRouter(
    prefix="/transacoes",
    tags=["transacoes"],
    dependencies=[Depends(verificar_origem), Depends(verificar_csrf)],
)

NAO_ENCONTRADA = HTTPException(status_code=404, detail="Transação não encontrada.")
CATEGORIA_INVALIDA = HTTPException(status_code=422, detail="Categoria inválida.")


async def _buscar_transacao(
    db: AsyncSession, id_transacao: uuid.UUID, usuario: Usuario
) -> Transacao:

    transacao = await db.scalar(
        select(Transacao).where(
            Transacao.id_transacao == id_transacao,
            Transacao.id_usuario == usuario.id_usuario,
        )
    )
    if transacao is None:
        raise NAO_ENCONTRADA
    return transacao


async def _validar_categoria(
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


@router.post("", status_code=201, response_model=TransacaoOut)
async def criar_transacao(
    dados: TransacaoCreate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    await _validar_categoria(db, dados.id_categoria, usuario)

    nova = Transacao(**dados.model_dump(), id_usuario=usuario.id_usuario)
    db.add(nova)
    await db.commit()
    await db.refresh(nova)
    return nova


@router.get("", response_model=list[TransacaoOut])
async def listar_transacoes(
    data_inicio: AwareDatetime | None = Query(default=None),
    data_fim: AwareDatetime | None = Query(default=None),
    tipo: TipoTransacao | None = Query(default=None),
    id_categoria: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    consulta = select(Transacao).where(Transacao.id_usuario == usuario.id_usuario)

    if data_inicio is not None:
        consulta = consulta.where(Transacao.data_hora >= data_inicio)
    if data_fim is not None:
        consulta = consulta.where(Transacao.data_hora < data_fim)
    if tipo is not None:
        consulta = consulta.where(Transacao.tipo == tipo)
    if id_categoria is not None:
        consulta = consulta.where(Transacao.id_categoria == id_categoria)

    consulta = (
        consulta.order_by(Transacao.data_hora.desc(), Transacao.id_transacao)
        .limit(limit)
        .offset(offset)
    )
    resultado = await db.scalars(consulta)
    return resultado.all()


@router.get("/{id_transacao}", response_model=TransacaoOut)
async def obter_transacao(
    id_transacao: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    return await _buscar_transacao(db, id_transacao, usuario)


@router.patch("/{id_transacao}", response_model=TransacaoOut)
async def editar_transacao(
    id_transacao: uuid.UUID,
    dados: TransacaoUpdate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    transacao = await _buscar_transacao(db, id_transacao, usuario)

    alteracoes = dados.model_dump(exclude_unset=True)
    if "id_categoria" in alteracoes:
        await _validar_categoria(db, alteracoes["id_categoria"], usuario)

    for campo, valor in alteracoes.items():
        setattr(transacao, campo, valor)

    await db.commit()
    await db.refresh(transacao)
    return transacao


@router.delete("/{id_transacao}", status_code=204)
async def apagar_transacao(
    id_transacao: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    transacao = await _buscar_transacao(db, id_transacao, usuario)
    await db.delete(transacao)
    await db.commit()
    return Response(status_code=204)
