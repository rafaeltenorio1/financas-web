from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.log_tentativa import LogTentativa
from utils.config import settings


async def _contar_falhas(db: AsyncSession, coluna, valor, desde: datetime) -> int:
    consulta = (
        select(func.count())
        .select_from(LogTentativa)
        .where(
            coluna == valor,
            LogTentativa.sucesso.is_(False),
            LogTentativa.ocorrida_em > desde,
        )
    )
    return await db.scalar(consulta) or 0


def _inicio_janela(agora: datetime) -> datetime:
    return agora - timedelta(minutes=settings.LOGIN_JANELA_MIN)


async def _falhas_do_email(db: AsyncSession, email: str, agora: datetime) -> int:
    inicio_janela = _inicio_janela(agora)

    # Só conta as falhas posteriores ao último sucesso deste e-mail.
    ultimo_sucesso = await db.scalar(
        select(func.max(LogTentativa.ocorrida_em)).where(
            LogTentativa.email_tentativa == email,
            LogTentativa.sucesso.is_(True),
        )
    )
    desde_email = max(inicio_janela, ultimo_sucesso) if ultimo_sucesso else inicio_janela

    return await _contar_falhas(db, LogTentativa.email_tentativa, email, desde_email)


async def esta_bloqueado(db: AsyncSession, email: str, ip: str, agora: datetime) -> bool:
    falhas_email = await _falhas_do_email(db, email, agora)
    falhas_ip = await _contar_falhas(db, LogTentativa.ip, ip, _inicio_janela(agora))

    return (
        falhas_email >= settings.LOGIN_MAX_FALHAS
        or falhas_ip >= settings.LOGIN_MAX_FALHAS_IP
    )


async def registrar_tentativa(
    db: AsyncSession, email: str, ip: str, sucesso: bool, agora: datetime) -> bool:

    db.add(
        LogTentativa(email_tentativa=email, ip=ip, ocorrida_em=agora, sucesso=sucesso)
    )
    await db.commit()

    if sucesso:
        return False
    return await _falhas_do_email(db, email, agora) == settings.LOGIN_MAX_FALHAS
