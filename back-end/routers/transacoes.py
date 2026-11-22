import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AwareDatetime
from sqlalchemy import case, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.categoria import Categoria
from models.enums import TipoTransacao
from models.transacao import Transacao
from models.usuario import Usuario
from schemas.resumo import ResumoOut
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
FUSO_INVALIDO = HTTPException(status_code=422, detail="Fuso horário inválido.")
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


def _soma_do_tipo(coluna_tipo, coluna_valor, tipo: TipoTransacao):
    return func.coalesce(func.sum(case((coluna_tipo == tipo, coluna_valor))), ZERO)


@router.get("/resumo", response_model=ResumoOut)
async def resumo_transacoes(
    data_inicio: AwareDatetime | None = Query(default=None),
    data_fim: AwareDatetime | None = Query(default=None),
    fuso: str = Query(default="America/Sao_Paulo", max_length=64),
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    fuso_existe = await db.scalar(
        text("SELECT 1 FROM pg_timezone_names WHERE name = :fuso"), {"fuso": fuso}
    )
    if fuso_existe is None:
        raise FUSO_INVALIDO

    filtros = [Transacao.id_usuario == usuario.id_usuario]
    if data_inicio is not None:
        filtros.append(Transacao.data_hora >= data_inicio)
    if data_fim is not None:
        filtros.append(Transacao.data_hora < data_fim)

    totais = (
        await db.execute(
            select(
                _soma_do_tipo(Transacao.tipo, Transacao.valor, TipoTransacao.RECEITA).label("receitas"),
                _soma_do_tipo(Transacao.tipo, Transacao.valor, TipoTransacao.DESPESA).label("despesas"),
            ).where(*filtros)
        )
    ).one()

    total_categoria = func.sum(Transacao.valor).label("total")
    por_categoria = (
        await db.execute(
            select(
                Transacao.id_categoria,
                Categoria.nome,
                Transacao.tipo,
                total_categoria,
                func.count().label("quantidade"),
            )
            .outerjoin(Categoria, Transacao.id_categoria == Categoria.id_categoria)
            .where(*filtros)
            .group_by(Transacao.id_categoria, Categoria.nome, Transacao.tipo)
            .order_by(total_categoria.desc(), Categoria.nome)
        )
    ).all()

    lancamentos = (
        select(
            func.to_char(func.timezone(fuso, Transacao.data_hora), "YYYY-MM").label("mes"),
            Transacao.tipo,
            Transacao.valor,
        )
        .where(*filtros)
        .subquery()
    )
    receitas_mes = _soma_do_tipo(lancamentos.c.tipo, lancamentos.c.valor, TipoTransacao.RECEITA)
    despesas_mes = _soma_do_tipo(lancamentos.c.tipo, lancamentos.c.valor, TipoTransacao.DESPESA)
    por_mes = (
        await db.execute(
            select(
                lancamentos.c.mes,
                receitas_mes.label("receitas"),
                despesas_mes.label("despesas"),
            )
            .group_by(lancamentos.c.mes)
            .order_by(lancamentos.c.mes)
        )
    ).all()

    return ResumoOut(
        receitas=totais.receitas,
        despesas=totais.despesas,
        saldo=totais.receitas - totais.despesas,
        por_categoria=[linha._asdict() for linha in por_categoria],
        por_mes=[
            {
                "mes": linha.mes,
                "receitas": linha.receitas,
                "despesas": linha.despesas,
                "saldo": linha.receitas - linha.despesas,
            }
            for linha in por_mes
        ],
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
