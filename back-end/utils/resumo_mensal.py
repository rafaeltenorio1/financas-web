from datetime import date, datetime

from sqlalchemy import Date, DateTime, bindparam, cast, extract, func, literal, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.conta_recorrente import ContaRecorrente
from models.usuario import Usuario
from utils.config import settings
from utils.email import enviar_email
from utils.mensagens_email import ContaPrevista, resumo_mensal
from utils.resumo import calcular_resumo
from utils.vencimentos import somar_meses

DIAS_DE_RECUPERACAO = 3


def _consulta_candidatos(agora: datetime):
    agora_local = func.timezone(
        Usuario.fuso, bindparam("agora", agora, type_=DateTime(timezone=True))
    )
    mes_atual = cast(func.date_trunc("month", agora_local), Date)

    return select(
        Usuario.id_usuario,
        Usuario.email,
        Usuario.nome,
        Usuario.fuso,
        mes_atual.label("mes_atual"),
    ).where(
        Usuario.resumo_mensal.is_(True),
        Usuario.email_verificado_em.is_not(None),
        extract("day", agora_local) <= DIAS_DE_RECUPERACAO,
        extract("hour", agora_local) >= settings.LEMBRETES_HORA,
        or_(Usuario.resumo_enviado_mes.is_(None), Usuario.resumo_enviado_mes < mes_atual),
    )


async def _reservar(db: AsyncSession, id_usuario, mes_atual: date) -> bool:
    reservado = await db.scalar(
        update(Usuario)
        .where(
            Usuario.id_usuario == id_usuario,
            or_(Usuario.resumo_enviado_mes.is_(None), Usuario.resumo_enviado_mes < mes_atual),
        )
        .values(resumo_enviado_mes=mes_atual)
        .returning(Usuario.id_usuario)
    )
    await db.commit()
    return reservado is not None


async def _inicio_do_dia(db: AsyncSession, fuso: str, dia: date) -> datetime:
    return await db.scalar(select(func.timezone(fuso, cast(literal(dia), DateTime))))


async def _contas_do_mes(db: AsyncSession, id_usuario, inicio: date, fim: date) -> list[ContaPrevista]:
    linhas = await db.execute(
        select(
            ContaRecorrente.nome,
            ContaRecorrente.valor,
            ContaRecorrente.tipo,
            ContaRecorrente.proximo_vencimento,
        )
        .where(
            ContaRecorrente.id_usuario == id_usuario,
            ContaRecorrente.ativa.is_(True),
            ContaRecorrente.proximo_vencimento >= inicio,
            ContaRecorrente.proximo_vencimento < fim,
        )
        .order_by(ContaRecorrente.proximo_vencimento, ContaRecorrente.nome)
    )
    return [
        ContaPrevista(nome=l.nome, valor=l.valor, tipo=l.tipo, vencimento=l.proximo_vencimento)
        for l in linhas
    ]


async def enviar_resumos(db: AsyncSession, agora: datetime) -> int:
    candidatos = (await db.execute(_consulta_candidatos(agora))).all()

    enviados = 0
    for candidato in candidatos:
        if not await _reservar(db, candidato.id_usuario, candidato.mes_atual):
            continue

        mes_atual = candidato.mes_atual
        mes_resumo = somar_meses(mes_atual, -1, 1)
        mes_comparacao = somar_meses(mes_atual, -2, 1)
        mes_seguinte = somar_meses(mes_atual, 1, 1)

        inicio_comparacao = await _inicio_do_dia(db, candidato.fuso, mes_comparacao)
        inicio_resumo = await _inicio_do_dia(db, candidato.fuso, mes_resumo)
        inicio_atual = await _inicio_do_dia(db, candidato.fuso, mes_atual)

        resumo = await calcular_resumo(
            db, candidato.id_usuario, inicio_resumo, inicio_atual, candidato.fuso
        )
        if resumo.receitas == 0 and resumo.despesas == 0:
            continue

        anterior = await calcular_resumo(
            db, candidato.id_usuario, inicio_comparacao, inicio_resumo, candidato.fuso
        )
        contas = await _contas_do_mes(db, candidato.id_usuario, mes_atual, mes_seguinte)

        conteudo = resumo_mensal(
            candidato.nome,
            mes_resumo,
            resumo,
            anterior.despesas,
            mes_comparacao,
            contas,
            mes_atual,
        )
        if await enviar_email(candidato.email, conteudo):
            enviados += 1
    return enviados
