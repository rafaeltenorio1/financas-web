import hashlib
import hmac

from fastapi import Cookie, Header, HTTPException, Request

from utils.config import settings

METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}


def gerar_csrf(token_sessao: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(), token_sessao.encode(), hashlib.sha256
    ).hexdigest()


async def verificar_origem(request: Request) -> None:
    if request.method in METODOS_SEGUROS:
        return
    if request.headers.get("origin") not in settings.CORS_ORIGINS:
        raise HTTPException(status_code=403, detail="Requisição não permitida.")


async def verificar_csrf(
    request: Request,
    token: str | None = Cookie(default=None, alias="sessao"),
    csrf: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if request.method in METODOS_SEGUROS:
        return
    if not token or not csrf or not hmac.compare_digest(csrf, gerar_csrf(token)):
        raise HTTPException(status_code=403, detail="Requisição não permitida.")