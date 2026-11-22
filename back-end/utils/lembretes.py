import asyncio
import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, and_, bindparam, cast, extract, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

import database
from models.conta_recorrente import ContaRecorrente
from models.enums import TipoLembrete
from models.notificacao_enviada import NotificacaoEnviada
from models.usuario import Usuario
from utils.config import settings
from utils.email import enviar_email
from utils.mensagens_email import ItemLembrete, lembrete_contas
from utils.resumo_mensal import enviar_resumos

logger = logging.getLogger(__name__)


def _consulta_pendentes(agora: datetime):
    agora_local = func.timezone(
        Usuario.fuso, bindparam("agora", agora, type_=DateTime(timezone=True))
    )
    hoje = cast(agora_local, Date)
    vencimento = ContaRecorrente.proximo_vencimento

    return (
        select(
            ContaRecorrente.id_conta_recorrente,
            ContaRecorrente.nome,
            ContaRecorrente.valor,
            ContaRecorrente.tipo,
            vencimento.label("vencimento"),
            Usuario.id_usuario,
            Usuario.email,
            Usuario.nome.label("nome_usuario"),
            hoje.label("hoje"),
        )
        .join(Usuario, Usuario.id_usuario == ContaRecorrente.id_usuario)
        .where(
            ContaRecorrente.ativa.is_(True),
            ContaRecorrente.avisar.is_(True),
            Usuario.email_verificado_em.is_not(None),
            extract("hour", agora_local) >= settings.LEMBRETES_HORA,
            or_(
                and_(
                    Usuario.lembrete_dias_antes > 0,
                    vencimento == hoje + Usuario.lembrete_dias_antes,
                ),
                and_(Usuario.lembrete_no_dia.is_(True), vencimento == hoje),
                and_(Usuario.lembrete_atraso.is_(True), vencimento == hoje - 1),
            ),
        )
    )


def _tipo_lembrete(vencimento, hoje) -> TipoLembrete:
    if vencimento == hoje:
        return TipoLembrete.NO_DIA
    if vencimento < hoje:
        return TipoLembrete.ATRASO
    return TipoLembrete.ANTECEDENCIA


async def enviar_lembretes(db: AsyncSession, agora: datetime) -> int:
    linhas = (await db.execute(_consulta_pendentes(agora))).all()
    if not linhas:
        return 0

    tipos = {linha.id_conta_recorrente: _tipo_lembrete(linha.vencimento, linha.hoje) for linha in linhas}
    reservadas = await db.execute(
        insert(NotificacaoEnviada)
        .values(
            [
                {
                    "id_notificacao_enviada": uuid.uuid4(),
                    "id_conta_recorrente": linha.id_conta_recorrente,
                    "tipo": tipos[linha.id_conta_recorrente],
                    "data_referencia": linha.vencimento,
                }
                for linha in linhas
            ]
        )
        .on_conflict_do_nothing(constraint="uq_notificacao_enviada_conta_tipo_data")
        .returning(NotificacaoEnviada.id_conta_recorrente)
    )
    contas_reservadas = set(reservadas.scalars())
    await db.commit()

    por_usuario: dict[uuid.UUID, tuple[str, str, date, list[ItemLembrete]]] = {}
    for linha in linhas:
        if linha.id_conta_recorrente not in contas_reservadas:
            continue
        _, _, _, itens = por_usuario.setdefault(
            linha.id_usuario, (linha.email, linha.nome_usuario, linha.hoje, [])
        )
        itens.append(
            ItemLembrete(
                lembrete=tipos[linha.id_conta_recorrente],
                nome=linha.nome,
                valor=linha.valor,
                tipo=linha.tipo,
                vencimento=linha.vencimento,
            )
        )

    enviados = 0
    for email, nome, hoje, itens in por_usuario.values():
        if await enviar_email(email, lembrete_contas(nome, itens, hoje)):
            enviados += 1
    return enviados


async def executar_lembretes_periodicos() -> None:
    while True:
        tarefas = [
            (enviar_lembretes, "Falha no envio de lembretes."),
            (enviar_resumos, "Falha no envio de resumos mensais."),
        ]
        for tarefa, mensagem_de_erro in tarefas:
            try:
                async with database.SessionLocal() as db:
                    await tarefa(db, datetime.now(timezone.utc))
            except Exception:
                logger.exception(mensagem_de_erro)
        await asyncio.sleep(settings.LEMBRETES_INTERVALO_MIN * 60)
