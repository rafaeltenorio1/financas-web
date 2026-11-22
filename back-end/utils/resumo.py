import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.categoria import Categoria
from models.enums import TipoTransacao
from models.transacao import Transacao
from schemas.resumo import ResumoOut
from schemas.transacao import TransacaoOut

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
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    Transacao.tipo == TipoTransacao.DESPESA,
                                    Transacao.id_conta_recorrente.is_not(None),
                                ),
                                Transacao.valor,
                            )
                        )
                    ),
                    ZERO,
                ).label("despesas_fixas"),
            ).where(*filtros)
        )
    ).one()

    maior_despesa = await db.scalar(
        select(Transacao)
        .where(*filtros, Transacao.tipo == TipoTransacao.DESPESA)
        .order_by(Transacao.valor.desc(), Transacao.data_hora.desc(), Transacao.id_transacao)
        .limit(1)
    )

    total_forma = func.sum(Transacao.valor).label("total")
    por_forma_pagamento = (
        await db.execute(
            select(
                Transacao.forma_pagamento,
                Transacao.tipo,
                total_forma,
                func.count().label("quantidade"),
            )
            .where(*filtros)
            .group_by(Transacao.forma_pagamento, Transacao.tipo)
            .order_by(total_forma.desc(), Transacao.tipo)
        )
    ).all()

    total_categoria = func.sum(Transacao.valor).label("total")
    por_categoria = (
        await db.execute(
            select(
                Transacao.id_categoria,
                Categoria.nome,
                Categoria.cor,
                Transacao.tipo,
                total_categoria,
                func.count().label("quantidade"),
            )
            .outerjoin(Categoria, Transacao.id_categoria == Categoria.id_categoria)
            .where(*filtros)
            .group_by(Transacao.id_categoria, Categoria.nome, Categoria.cor, Transacao.tipo)
            .order_by(total_categoria.desc(), Categoria.nome)
        )
    ).all()

    lancamentos = (
        select(
            func.to_char(func.timezone(fuso, Transacao.data_hora), "YYYY-MM").label("mes"),
            Transacao.tipo,
            Transacao.valor,
            Transacao.id_categoria,
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

    total_mes_categoria = func.sum(lancamentos.c.valor).label("total")
    linhas_mes_categoria = (
        await db.execute(
            select(
                lancamentos.c.mes,
                lancamentos.c.id_categoria,
                Categoria.nome,
                Categoria.cor,
                lancamentos.c.tipo,
                total_mes_categoria,
                func.count().label("quantidade"),
            )
            .outerjoin(Categoria, lancamentos.c.id_categoria == Categoria.id_categoria)
            .group_by(
                lancamentos.c.mes,
                lancamentos.c.id_categoria,
                Categoria.nome,
                Categoria.cor,
                lancamentos.c.tipo,
            )
            .order_by(lancamentos.c.mes, total_mes_categoria.desc(), Categoria.nome)
        )
    ).all()
    categorias_por_mes: dict[str, list[dict]] = {}
    for linha in linhas_mes_categoria:
        dados = linha._asdict()
        categorias_por_mes.setdefault(dados.pop("mes"), []).append(dados)

    return ResumoOut(
        receitas=totais.receitas,
        despesas=totais.despesas,
        saldo=totais.receitas - totais.despesas,
        despesas_fixas=totais.despesas_fixas,
        maior_despesa=TransacaoOut.model_validate(maior_despesa) if maior_despesa else None,
        por_categoria=[linha._asdict() for linha in por_categoria],
        por_forma_pagamento=[linha._asdict() for linha in por_forma_pagamento],
        por_mes=[
            {
                "mes": linha.mes,
                "receitas": linha.receitas,
                "despesas": linha.despesas,
                "saldo": linha.receitas - linha.despesas,
                "categorias": categorias_por_mes.get(linha.mes, []),
            }
            for linha in por_mes
        ],
    )
