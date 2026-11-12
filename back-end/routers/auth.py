from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select, delete

from datetime import datetime, timedelta, timezone

from database import get_db

from utils.security import gerar_hash, verificar_senha, gerar_token, hash_token
from utils.config import settings
from utils.auth import get_usuario_atual
from utils.tentativas import esta_bloqueado, registrar_tentativa, _contar_falhas

from models.usuario import Usuario
from models.log_tentativa import LogTentativa
from models.sessao import Sessao

from schemas.usuario import UsuarioOut, UsuarioCreate
from schemas.auth import LoginIn, TrocaSenhaIn, MensagemOut

router = APIRouter(prefix="/auth", tags=["auth"])


async def contar_falhas(db: AsyncSession, coluna, valor, desde) -> int:
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


@router.post("/register", status_code=201, response_model=UsuarioOut)
async def register(dados: UsuarioCreate, db: AsyncSession = Depends(get_db)):
    novo = Usuario(
        nome = dados.nome,
        email = dados.email,
        senha_hash=await gerar_hash(dados.senha),
    )
    db.add(novo)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível concluir o cadastro.")
    await db.refresh(novo)
    return novo


@router.post("/login", response_model=UsuarioOut)
async def login(
    dados: LoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host
    agora = datetime.now(timezone.utc)

    if await esta_bloqueado(db, dados.email, ip, agora):
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
            headers={"Retry-After": str(settings.LOGIN_JANELA_MIN * 60)},
        )

    usuario = await db.scalar(select(Usuario).where(Usuario.email == dados.email))
    hash_armazenado = usuario.senha_hash if usuario else None
    senha_valida = await verificar_senha(dados.senha, hash_armazenado)
    sucesso = usuario is not None and senha_valida

    await registrar_tentativa(db, dados.email, ip, sucesso, agora)
    if not sucesso:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")

    token, token_hash = gerar_token()
    db.add(
        Sessao(
            id_usuario=usuario.id_usuario,
            token_hash=token_hash,
            expira_em=agora + timedelta(days=settings.SESSAO_DURACAO_DIAS),
        )
    )
    await db.commit()

    response.set_cookie(
        key="sessao",
        value=token,
        max_age=settings.SESSAO_DURACAO_DIAS * 86400,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return usuario


@router.get("/me", response_model=UsuarioOut)
async def me(usuario: Usuario = Depends(get_usuario_atual)):
    return usuario


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    token: str | None = Cookie(default=None, alias="sessao"),
    db: AsyncSession = Depends(get_db),
):
    if token:
        await db.execute(delete(Sessao).where(Sessao.token_hash == hash_token(token)))
        await db.commit()

    response.delete_cookie(
        key="sessao",
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )


@router.post("/trocar-senha", response_model=MensagemOut)
async def trocar_senha(
    dados: TrocaSenhaIn,
    request: Request,
    usuario: Usuario = Depends(get_usuario_atual),
    token: str | None = Cookie(default=None, alias="sessao"),
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host
    agora = datetime.now(timezone.utc)

    if await esta_bloqueado(db, usuario.email, ip, agora):
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Tente novamente mais tarde.",
            headers={"Retry-After": str(settings.LOGIN_JANELA_MIN * 60)},
        )

    senha_valida = await verificar_senha(dados.senha_atual, usuario.senha_hash)
    await registrar_tentativa(db, usuario.email, ip, senha_valida, agora)
    if not senha_valida:
        raise HTTPException(status_code=401, detail="Senha atual incorreta.")

    usuario.senha_hash = await gerar_hash(dados.senha_nova)
    await db.execute(
        delete(Sessao).where(
            Sessao.id_usuario == usuario.id_usuario,
            Sessao.token_hash != hash_token(token),
        )
    )
    await db.commit()
    return MensagemOut(mensagem="Senha alterada com sucesso.")

    