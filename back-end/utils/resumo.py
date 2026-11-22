import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.categoria import Categoria
from models.enums import TipoTransacao
from models.transacao import Transacao
from schemas.resumo import ResumoOut

ZERO = Decimal("0.00")


def _soma_do_tipo(coluna_tipo, coluna_valor, tipo: TipoTransacao):
    return func.coalesce(func.sum(case((coluna_tipo == tipo, coluna_valor))), ZERO)


async def calcular_resumo(
    db: AsyncSession,
    id_usuario: uuid.UUID,
    data_inicio: datetime | None,
    data_fim: datetime | None,
    fuso: str,
) -> ResumoOut:
    filtros = [Transacao.id_usuario == id_usuario]
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
