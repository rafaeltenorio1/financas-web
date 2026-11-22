import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AwareDatetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.enums import TipoTransacao
from models.transacao import Transacao
from models.usuario import Usuario
from schemas.resumo import ResumoOut
from schemas.transacao import TransacaoCreate, TransacaoOut, TransacaoUpdate
from utils.auth import get_usuario_atual
from utils.categorias import validar_categoria
from utils.csrf import verificar_csrf, verificar_origem
from utils.fuso import validar_fuso
from utils.resumo import calcular_resumo

router = APIRouter(
    prefix="/transacoes",
    tags=["transacoes"],
    dependencies=[Depends(verificar_origem), Depends(verificar_csrf)],
)

NAO_ENCONTRADA = HTTPException(status_code=404, detail="Transação não encontrada.")


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


@router.post("", status_code=201, response_model=TransacaoOut)
async def criar_transacao(
    dados: TransacaoCreate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    await validar_categoria(db, dados.id_categoria, usuario)

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


@router.get("/resumo", response_model=ResumoOut)
async def resumo_transacoes(
    data_inicio: AwareDatetime | None = Query(default=None),
    data_fim: AwareDatetime | None = Query(default=None),
    fuso: str = Query(default="America/Sao_Paulo", max_length=64),
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    await validar_fuso(db, fuso)
    return await calcular_resumo(db, usuario.id_usuario, data_inicio, data_fim, fuso)


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
        await validar_categoria(db, alteracoes["id_categoria"], usuario)

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
