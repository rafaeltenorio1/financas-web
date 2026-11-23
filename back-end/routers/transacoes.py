import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AwareDatetime
from sqlalchemy import Date, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.categoria import Categoria
from models.conta_recorrente import ContaRecorrente
from models.enums import TipoTransacao
from models.transacao import Transacao
from models.usuario import Usuario
from schemas.resumo import ResumoOut
from schemas.transacao import TotaisOut, TransacaoCreate, TransacaoOut, TransacaoUpdate
from utils.auth import get_usuario_atual
from utils.categorias import validar_categoria
from utils.csrf import verificar_csrf, verificar_origem
from utils.exportacao import gerar_csv
from utils.fuso import validar_fuso
from utils.resumo import calcular_resumo

router = APIRouter(
    prefix="/transacoes",
    tags=["transacoes"],
    dependencies=[Depends(verificar_origem), Depends(verificar_csrf)],
)

NAO_ENCONTRADA = HTTPException(status_code=404, detail="Transação não encontrada.")
BUSCA_MAXIMA = 100
ZERO = Decimal("0.00")


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


def _filtros(
    usuario: Usuario,
    data_inicio: datetime | None,
    data_fim: datetime | None,
    tipo: TipoTransacao | None,
    id_categoria: uuid.UUID | None,
    busca: str | None = None,
) -> list:
    filtros = [Transacao.id_usuario == usuario.id_usuario]
    if data_inicio is not None:
        filtros.append(Transacao.data_hora >= data_inicio)
    if data_fim is not None:
        filtros.append(Transacao.data_hora < data_fim)
    if tipo is not None:
        filtros.append(Transacao.tipo == tipo)
    if id_categoria is not None:
        filtros.append(Transacao.id_categoria == id_categoria)
    termo = (busca or "").strip()
    if termo:
        escapado = termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        padrao = func.unaccent(f"%{escapado}%")

        def parecido(coluna):
            return func.unaccent(coluna).ilike(padrao, escape="\\")

        filtros.append(
            or_(
                parecido(Transacao.nome),
                parecido(Transacao.descricao),
                Transacao.id_categoria.in_(select(Categoria.id_categoria).where(parecido(Categoria.nome))),
            )
        )
    return filtros


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
    busca: str | None = Query(default=None, max_length=BUSCA_MAXIMA),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    filtros = _filtros(usuario, data_inicio, data_fim, tipo, id_categoria, busca)
    consulta = (
        select(Transacao)
        .where(*filtros)
        .order_by(Transacao.data_hora.desc(), Transacao.id_transacao)
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


@router.get("/totais", response_model=TotaisOut)
async def totais_transacoes(
    data_inicio: AwareDatetime | None = Query(default=None),
    data_fim: AwareDatetime | None = Query(default=None),
    tipo: TipoTransacao | None = Query(default=None),
    id_categoria: uuid.UUID | None = Query(default=None),
    busca: str | None = Query(default=None, max_length=BUSCA_MAXIMA),
    fuso: str = Query(default="America/Sao_Paulo", max_length=64),
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    await validar_fuso(db, fuso)
    filtros = _filtros(usuario, data_inicio, data_fim, tipo, id_categoria, busca)
    dia = cast(func.timezone(fuso, Transacao.data_hora), Date).label("dia")

    def soma(tipo_somado: TipoTransacao):
        return func.coalesce(func.sum(case((Transacao.tipo == tipo_somado, Transacao.valor))), ZERO)

    linhas = (
        await db.execute(
            select(
                dia,
                soma(TipoTransacao.RECEITA).label("receitas"),
                soma(TipoTransacao.DESPESA).label("despesas"),
                func.count().label("quantidade"),
            )
            .where(*filtros)
            .group_by(dia)
            .order_by(dia.desc())
        )
    ).all()

    return TotaisOut(
        receitas=sum((linha.receitas for linha in linhas), ZERO),
        despesas=sum((linha.despesas for linha in linhas), ZERO),
        quantidade=sum(linha.quantidade for linha in linhas),
        por_dia=[{"dia": linha.dia, "receitas": linha.receitas, "despesas": linha.despesas} for linha in linhas],
    )


@router.get("/exportar")
async def exportar_transacoes(
    data_inicio: AwareDatetime | None = Query(default=None),
    data_fim: AwareDatetime | None = Query(default=None),
    tipo: TipoTransacao | None = Query(default=None),
    id_categoria: uuid.UUID | None = Query(default=None),
    busca: str | None = Query(default=None, max_length=BUSCA_MAXIMA),
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    filtros = _filtros(usuario, data_inicio, data_fim, tipo, id_categoria, busca)
    consulta = (
        select(
            func.timezone(usuario.fuso, Transacao.data_hora).label("data_local"),
            Transacao.tipo,
            Transacao.nome,
            Categoria.nome.label("categoria"),
            Transacao.valor,
            Transacao.forma_pagamento,
            Transacao.descricao,
            ContaRecorrente.nome.label("conta_recorrente"),
        )
        .outerjoin(Categoria, Categoria.id_categoria == Transacao.id_categoria)
        .outerjoin(
            ContaRecorrente,
            ContaRecorrente.id_conta_recorrente == Transacao.id_conta_recorrente,
        )
        .where(*filtros)
        .order_by(Transacao.data_hora, Transacao.id_transacao)
    )
    linhas = (await db.execute(consulta)).all()
    hoje = await db.scalar(select(cast(func.timezone(usuario.fuso, func.now()), Date)))

    return Response(
        content=gerar_csv(linhas),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="financas-transacoes-{hoje.isoformat()}.csv"',
            "Cache-Control": "no-store",
        },
    )


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
