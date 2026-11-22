import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

import database
from models.log_tentativa import LogTentativa
from models.sessao import Sessao
from utils.config import settings

logger = logging.getLogger(__name__)


async def limpar_dados_vencidos(db: AsyncSession, agora: datetime) -> tuple[int, int]:
    limite_inatividade = agora - timedelta(minutes=settings.SESSAO_INATIVIDADE_MIN)
    limite_tentativas = agora - timedelta(days=settings.TENTATIVAS_RETENCAO_DIAS)

    sessoes = await db.execute(
        delete(Sessao).where(
            or_(
                Sessao.expira_em <= agora,
                Sessao.ultimo_acesso_em < limite_inatividade,
            )
        )
    )
    tentativas = await db.execute(
        delete(LogTentativa).where(LogTentativa.ocorrida_em < limite_tentativas)
    )
    await db.commit()

    return sessoes.rowcount, tentativas.rowcount


async def executar_limpeza_periodica() -> None:
    while True:
        try:
            async with database.SessionLocal() as db:
                await limpar_dados_vencidos(db, datetime.now(timezone.utc))
        except Exception:
            logger.exception("Falha na limpeza de sessões e tentativas.")
        await asyncio.sleep(settings.LIMPEZA_INTERVALO_MIN * 60)
