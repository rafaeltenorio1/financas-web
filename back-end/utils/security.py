import asyncio
import hashlib
import secrets

from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()  # Argon2
# Hash descartável, usado para gastar o mesmo tempo quando o e-mail não existe.
_HASH_FALSO = _hasher.hash(secrets.token_urlsafe(16))


async def gerar_hash(senha: str) -> str:
    # O Argon2 é lento de propósito; fora da thread principal ele não trava a API.
    return await asyncio.to_thread(_hasher.hash, senha)


async def verificar_senha(senha: str, hash_armazenado: str | None) -> bool:
    if hash_armazenado is None:
        await asyncio.to_thread(_hasher.verify, senha, _HASH_FALSO)
        return False
    return await asyncio.to_thread(_hasher.verify, senha, hash_armazenado)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def gerar_token() -> tuple[str, str]:
    """Devolve (token para o cookie, hash para o banco)."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)