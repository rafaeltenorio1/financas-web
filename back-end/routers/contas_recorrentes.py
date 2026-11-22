import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.conta_recorrente import ContaRecorrente
from models.enums import TipoTransacao
from models.transacao import Transacao
from models.usuario import Usuario
from schemas.conta_recorrente import (
    ContaRecorrenteCreate,
    ContaRecorrenteOut,
    ContaRecorrenteUpdate,
    PagamentoOut,
    PagarIn,
)
from utils.auth import get_usuario_atual
from utils.categorias import validar_categoria
from utils.csrf import verificar_csrf, verificar_origem
from utils.vencimentos import calcular_proximo_vencimento

router = APIRouter(
    prefix="/contas-recorrentes",
    tags=["contas-recorrentes"],
    dependencies=[Depends(verificar_origem), Depends(verificar_csrf)],
)

NAO_ENCONTRADA = HTTPException(status_code=404, detail="Conta recorrente não encontrada.")
CONTA_INATIVA = HTTPException(status_code=409, detail="A conta recorrente está inativa.")


async def _buscar_conta(
    db: AsyncSession, id_conta: uuid.UUID, usuario: Usuario, travar: bool = False
) -> ContaRecorrente:
    consulta = select(ContaRecorrente).where(
        ContaRecorrente.id_conta_recorrente == id_conta,
        ContaRecorrente.id_usuario == usuario.id_usuario,
    )
    if travar:
        consulta = consulta.with_for_update()
    conta = await db.scalar(consulta)
    if conta is None:
        raise NAO_ENCONTRADA
    return conta


def _validar_estado(conta: ContaRecorrente) -> None:
    if conta.proximo_vencimento < conta.data_inicio:
        raise HTTPException(
            status_code=422, detail="O próximo vencimento não pode ser anterior ao início."
        )
    if conta.data_fim is not None and conta.data_fim < conta.data_inicio:
        raise HTTPException(status_code=422, detail="O fim não pode ser anterior ao início.")
    if conta.ativa and conta.data_fim is not None and conta.proximo_vencimento > conta.data_fim:
        raise HTTPException(
            status_code=422, detail="O próximo vencimento passa do fim da conta recorrente."
        )


def _avancar(conta: ContaRecorrente) -> None:
    conta.proximo_vencimento = calcular_proximo_vencimento(
        conta.proximo_vencimento, conta.periodicidade, conta.data_inicio
    )
    if conta.data_fim is not None and conta.proximo_vencimento > conta.data_fim:
        conta.ativa = False


@router.post("", status_code=201, response_model=ContaRecorrenteOut)
async def criar_conta(
    dados: ContaRecorrenteCreate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    await validar_categoria(db, dados.id_categoria, usuario)

    nova = ContaRecorrente(
        **dados.model_dump(),
        id_usuario=usuario.id_usuario,
        proximo_vencimento=dados.data_inicio,
    )
    db.add(nova)
    await db.commit()
    await db.refresh(nova)
    return nova


@router.get("", response_model=list[ContaRecorrenteOut])
async def listar_contas(
    ativa: bool | None = Query(default=None),
    tipo: TipoTransacao | None = Query(default=None),
    vence_ate: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    consulta = select(ContaRecorrente).where(ContaRecorrente.id_usuario == usuario.id_usuario)

    if ativa is not None:
        consulta = consulta.where(ContaRecorrente.ativa.is_(ativa))
    if tipo is not None:
        consulta = consulta.where(ContaRecorrente.tipo == tipo)
    if vence_ate is not None:
        consulta = consulta.where(ContaRecorrente.proximo_vencimento <= vence_ate)

    consulta = (
        consulta.order_by(
            ContaRecorrente.proximo_vencimento,
            ContaRecorrente.nome,
            ContaRecorrente.id_conta_recorrente,
        )
        .limit(limit)
        .offset(offset)
    )
    resultado = await db.scalars(consulta)
    return resultado.all()


@router.get("/{id_conta}", response_model=ContaRecorrenteOut)
async def obter_conta(
    id_conta: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    return await _buscar_conta(db, id_conta, usuario)


@router.patch("/{id_conta}", response_model=ContaRecorrenteOut)
async def editar_conta(
    id_conta: uuid.UUID,
    dados: ContaRecorrenteUpdate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    conta = await _buscar_conta(db, id_conta, usuario, travar=True)

    alteracoes = dados.model_dump(exclude_unset=True)
    if "id_categoria" in alteracoes:
        await validar_categoria(db, alteracoes["id_categoria"], usuario)

    for campo, valor in alteracoes.items():
        setattr(conta, campo, valor)
    _validar_estado(conta)

    await db.commit()
    await db.refresh(conta)
    return conta


@router.delete("/{id_conta}", status_code=204)
async def apagar_conta(
    id_conta: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    conta = await _buscar_conta(db, id_conta, usuario)
    await db.delete(conta)
    await db.commit()
    return Response(status_code=204)


@router.post("/{id_conta}/pagar", status_code=201, response_model=PagamentoOut)
async def pagar_conta(
    id_conta: uuid.UUID,
    dados: PagarIn | None = None,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    dados = dados or PagarIn()
    conta = await _buscar_conta(db, id_conta, usuario, travar=True)
    if not conta.ativa:
        raise CONTA_INATIVA

    informados = dados.model_dump(exclude_unset=True)
    transacao = Transacao(
        id_usuario=usuario.id_usuario,
        id_categoria=conta.id_categoria,
        id_conta_recorrente=conta.id_conta_recorrente,
        nome=conta.nome,
        valor=informados.get("valor", conta.valor),
        data_hora=informados.get("data_hora", datetime.now(timezone.utc)),
        tipo=conta.tipo,
        forma_pagamento=informados.get("forma_pagamento", conta.forma_pagamento),
        descricao=informados.get("descricao"),
    )
    db.add(transacao)
    _avancar(conta)

    await db.commit()
    await db.refresh(transacao)
    await db.refresh(conta)
    return PagamentoOut(transacao=transacao, conta=conta)


@router.post("/{id_conta}/pular", response_model=ContaRecorrenteOut)
async def pular_vencimento(
    id_conta: uuid.UUID,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    conta = await _buscar_conta(db, id_conta, usuario, travar=True)
    if not conta.ativa:
        raise CONTA_INATIVA

    _avancar(conta)
    await db.commit()
    await db.refresh(conta)
    return conta
