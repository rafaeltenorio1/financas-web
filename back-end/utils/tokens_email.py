from datetime import datetime, timedelta

from sqlalchemy import Row, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import FinalidadeToken
from models.token_email import TokenEmail
from models.usuario import Usuario
from utils.config import settings
from utils.security import gerar_token, hash_token

PAGINAS = {
    FinalidadeToken.VERIFICACAO: "verificar-email",
    FinalidadeToken.REDEFINIR_SENHA: "redefinir-senha",
    FinalidadeToken.TROCAR_EMAIL: "confirmar-email",
}


def validade(finalidade: FinalidadeToken) -> timedelta:
    if finalidade is FinalidadeToken.VERIFICACAO:
        return timedelta(hours=settings.TOKEN_VERIFICACAO_HORAS)
    if finalidade is FinalidadeToken.REDEFINIR_SENHA:
        return timedelta(minutes=settings.TOKEN_REDEFINIR_SENHA_MIN)
    return timedelta(minutes=settings.TOKEN_TROCAR_EMAIL_MIN)


def montar_link(finalidade: FinalidadeToken, token: str) -> str:
    return f"{settings.FRONT_URL.rstrip('/')}/#/{PAGINAS[finalidade]}?token={token}"


async def criar_token(
    db: AsyncSession,
    usuario: Usuario,
    finalidade: FinalidadeToken,
    agora: datetime,
    email_novo: str | None = None,
) -> str | None:
    criado_em_anterior = await db.scalar(
        select(TokenEmail.criado_em).where(
            TokenEmail.id_usuario == usuario.id_usuario,
            TokenEmail.finalidade == finalidade,
        )
    )
    intervalo = timedelta(minutes=settings.TOKEN_INTERVALO_ENVIO_MIN)
    if criado_em_anterior is not None and agora - criado_em_anterior < intervalo:
        return None

    await db.execute(
        delete(TokenEmail).where(
            TokenEmail.id_usuario == usuario.id_usuario,
            TokenEmail.finalidade == finalidade,
        )
    )
    token, token_hash = gerar_token()
    db.add(
        TokenEmail(
            id_usuario=usuario.id_usuario,
            finalidade=finalidade,
            token_hash=token_hash,
            email_novo=email_novo,
            criado_em=agora,
            expira_em=agora + validade(finalidade),
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        await db.refresh(usuario)
        return None
    return token


async def consumir_token(
    db: AsyncSession, token: str, finalidade: FinalidadeToken, agora: datetime
) -> Row | None:
    resultado = await db.execute(
        delete(TokenEmail)
        .where(
            TokenEmail.token_hash == hash_token(token),
            TokenEmail.finalidade == finalidade,
            TokenEmail.expira_em > agora,
        )
        .returning(TokenEmail.id_usuario, TokenEmail.email_novo)
    )
    return resultado.one_or_none()


async def apagar_tokens_do_usuario(db: AsyncSession, usuario: Usuario) -> None:
    await db.execute(delete(TokenEmail).where(TokenEmail.id_usuario == usuario.id_usuario))
