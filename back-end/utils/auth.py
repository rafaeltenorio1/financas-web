from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.sessao import Sessao
from models.usuario import Usuario
from utils.config import settings
from utils.security import hash_token

NAO_AUTENTICADO = HTTPException(status_code=401, detail="Não autenticado.")


async def get_usuario_atual(
    token: str | None = Cookie(default=None, alias="sessao"),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    if not token:
        raise NAO_AUTENTICADO

    sessao = await db.scalar(
        select(Sessao).where(Sessao.token_hash == hash_token(token))
    )
    if sessao is None:
        raise NAO_AUTENTICADO

    agora = datetime.now(timezone.utc)
    inativa = agora - sessao.ultimo_acesso_em > timedelta(minutes=settings.SESSAO_INATIVIDADE_MIN)
    if sessao.expira_em <= agora or inativa:
        await db.delete(sessao)
        await db.commit()
        raise NAO_AUTENTICADO

    # Evita uma gravação por requisição: só renova se passou mais de 1 minuto.
    if agora - sessao.ultimo_acesso_em > timedelta(minutes=1):
        sessao.ultimo_acesso_em = agora
        await db.commit()

    return await db.get(Usuario, sessao.id_usuario)