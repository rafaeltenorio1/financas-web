import base64
import hmac
import re
import secrets
from datetime import datetime

import pyotp
from cryptography.fernet import Fernet
from sqlalchemy import delete, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.codigo_recuperacao import CodigoRecuperacao
from models.usuario import Usuario
from utils.config import settings
from utils.security import hash_token

QUANTIDADE_CODIGOS_RECUPERACAO = 10

_fernet = Fernet(settings.TOTP_CHAVE)
_CODIGO_TOTP = re.compile(r"\d{6}")


def gerar_segredo() -> str:
    return pyotp.random_base32()


def cifrar(segredo: str) -> str:
    return _fernet.encrypt(segredo.encode()).decode()


def decifrar(segredo_cifrado: str) -> str:
    return _fernet.decrypt(segredo_cifrado.encode()).decode()


def gerar_uri(segredo: str, email: str) -> str:
    return pyotp.TOTP(segredo).provisioning_uri(name=email, issuer_name=settings.TOTP_EMISSOR)


def _passo_do_codigo(segredo: str, codigo: str, agora: datetime) -> int | None:
    totp = pyotp.TOTP(segredo)
    passo_atual = totp.timecode(agora)
    for passo in (passo_atual - 1, passo_atual, passo_atual + 1):
        if hmac.compare_digest(totp.generate_otp(passo), codigo):
            return passo
    return None


async def verificar_totp(db: AsyncSession, usuario: Usuario, codigo: str, agora: datetime) -> bool:
    if usuario.totp_segredo is None or not _CODIGO_TOTP.fullmatch(codigo):
        return False

    passo = _passo_do_codigo(decifrar(usuario.totp_segredo), codigo, agora)
    if passo is None:
        return False

    resultado = await db.execute(
        update(Usuario)
        .where(
            Usuario.id_usuario == usuario.id_usuario,
            or_(Usuario.totp_ultimo_passo.is_(None), Usuario.totp_ultimo_passo < passo),
        )
        .values(totp_ultimo_passo=passo)
    )
    return resultado.rowcount == 1


def _normalizar_codigo_recuperacao(codigo: str) -> str:
    return re.sub(r"[\s-]", "", codigo).upper()


def gerar_codigos_recuperacao() -> list[str]:
    codigos = []
    for _ in range(QUANTIDADE_CODIGOS_RECUPERACAO):
        bruto = base64.b32encode(secrets.token_bytes(10)).decode()
        codigos.append("-".join(bruto[i:i + 4] for i in range(0, 16, 4)))
    return codigos


async def substituir_codigos_recuperacao(db: AsyncSession, usuario: Usuario) -> list[str]:
    await db.execute(
        delete(CodigoRecuperacao).where(CodigoRecuperacao.id_usuario == usuario.id_usuario)
    )
    codigos = gerar_codigos_recuperacao()
    db.add_all(
        CodigoRecuperacao(
            id_usuario=usuario.id_usuario,
            codigo_hash=hash_token(_normalizar_codigo_recuperacao(codigo)),
        )
        for codigo in codigos
    )
    return codigos


async def usar_codigo_recuperacao(
    db: AsyncSession, usuario: Usuario, codigo: str, agora: datetime
) -> bool:
    resultado = await db.execute(
        update(CodigoRecuperacao)
        .where(
            CodigoRecuperacao.id_usuario == usuario.id_usuario,
            CodigoRecuperacao.codigo_hash == hash_token(_normalizar_codigo_recuperacao(codigo)),
            CodigoRecuperacao.usado_em.is_(None),
        )
        .values(usado_em=agora)
    )
    return resultado.rowcount == 1


async def verificar_segundo_fator(
    db: AsyncSession, usuario: Usuario, codigo: str, agora: datetime
) -> bool:
    if not usuario.dois_fatores:
        return False
    if _CODIGO_TOTP.fullmatch(codigo):
        return await verificar_totp(db, usuario, codigo, agora)
    return await usar_codigo_recuperacao(db, usuario, codigo, agora)
