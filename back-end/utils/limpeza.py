import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

import database
from models.desafio_2fa import Desafio2FA
from models.log_tentativa import LogTentativa
from models.notificacao_enviada import NotificacaoEnviada
from models.sessao import Sessao
from models.token_email import TokenEmail
from utils.auth import inatividade_maxima
from utils.config import settings

logger = logging.getLogger(__name__)


async def limpar_dados_vencidos(db: AsyncSession, agora: datetime) -> tuple[int, int, int, int, int]:
    limite_tentativas = agora - timedelta(days=settings.TENTATIVAS_RETENCAO_DIAS)
    limite_notificacoes = agora - timedelta(days=settings.NOTIFICACOES_RETENCAO_DIAS)

    sessoes = await db.execute(
        delete(Sessao).where(
            or_(
                Sessao.expira_em <= agora,
                and_(
                    Sessao.lembrar.is_(False),
                    Sessao.ultimo_acesso_em < agora - inatividade_maxima(False),
                ),
                and_(
                    Sessao.lembrar.is_(True),
                    Sessao.ultimo_acesso_em < agora - inatividade_maxima(True),
                ),
            )
        )
    )
    tentativas = await db.execute(
        delete(LogTentativa).where(LogTentativa.ocorrida_em < limite_tentativas)
    )
    desafios = await db.execute(delete(Desafio2FA).where(Desafio2FA.expira_em <= agora))
    tokens = await db.execute(delete(TokenEmail).where(TokenEmail.expira_em <= agora))
    notificacoes = await db.execute(
        delete(NotificacaoEnviada).where(NotificacaoEnviada.enviada_em < limite_notificacoes)
    )
    await db.commit()

    return (
        sessoes.rowcount,
        tentativas.rowcount,
        desafios.rowcount,
        tokens.rowcount,
        notificacoes.rowcount,
    )


async def executar_limpeza_periodica() -> None:
    while True:
        try:
            async with database.SessionLocal() as db:
                await limpar_dados_vencidos(db, datetime.now(timezone.utc))
        except Exception:
            logger.exception("Falha na limpeza de dados vencidos.")
        await asyncio.sleep(settings.LIMPEZA_INTERVALO_MIN * 60)
