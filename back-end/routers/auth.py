from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, delete

from datetime import datetime, timedelta, timezone

from database import get_db

from utils.security import gerar_hash, verificar_senha, gerar_token, hash_token
from utils.config import settings
from utils.auth import duracao_maxima, get_usuario_atual
from utils.tentativas import esta_bloqueado, registrar_tentativa
from utils.csrf import verificar_origem, verificar_csrf, gerar_csrf
from utils.totp import (
    cifrar,
    gerar_segredo,
    gerar_uri,
    substituir_codigos_recuperacao,
    verificar_segundo_fator,
    verificar_totp,
)

from models.usuario import Usuario
from models.sessao import Sessao
from models.codigo_recuperacao import CodigoRecuperacao
from models.desafio_2fa import Desafio2FA

from schemas.usuario import UsuarioOut, UsuarioCreate, UsuarioUpdate
from schemas.auth import (
    LoginIn,
    TrocaSenhaIn,
    MensagemOut,
    CSRFTokenOut,
    ExcluirContaIn,
    CodigoIn,
    SenhaECodigoIn,
    Requer2FAOut,
    Iniciar2FAOut,
    CodigosRecuperacaoOut,
)

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(verificar_origem)])

COOKIE_DESAFIO = "desafio_2fa"
CAMINHO_COOKIE_DESAFIO = "/auth/login"
DESAFIO_INVALIDO = HTTPException(status_code=401, detail="Login expirado. Entre novamente.")
SENHA_OU_CODIGO_INCORRETOS = "Senha ou código incorretos."


def _erro_bloqueio(detalhe: str) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail=detalhe,
        headers={"Retry-After": str(settings.LOGIN_JANELA_MIN * 60)},
    )


async def _confirmar_senha(
    db: AsyncSession,
    usuario: Usuario,
    senha: str,
    request: Request,
    erro: str,
    codigo: str | None = None,
    so_totp: bool = False,
) -> None:
    ip = request.client.host
    agora = datetime.now(timezone.utc)

    if await esta_bloqueado(db, usuario.email, ip, agora):
        raise _erro_bloqueio("Muitas tentativas. Tente novamente mais tarde.")

    valido = await verificar_senha(senha, usuario.senha_hash)
    if valido and codigo is not None:
        verificar = verificar_totp if so_totp else verificar_segundo_fator
        valido = await verificar(db, usuario, codigo, agora)

    await registrar_tentativa(db, usuario.email, ip, valido, agora)
    if not valido:
        raise HTTPException(status_code=401, detail=erro)


def _apagar_cookie(response: Response) -> None:
    response.delete_cookie(
        key="sessao",
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )


async def _criar_sessao(
    db: AsyncSession, response: Response, usuario: Usuario, agora: datetime, lembrar: bool
) -> None:
    token, token_hash = gerar_token()
    duracao = duracao_maxima(lembrar)
    db.add(
        Sessao(
            id_usuario=usuario.id_usuario,
            token_hash=token_hash,
            expira_em=agora + duracao,
            lembrar=lembrar,
        )
    )
    await db.commit()

    response.set_cookie(
        key="sessao",
        value=token,
        max_age=int(duracao.total_seconds()) if lembrar else None,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


async def _apagar_outras_sessoes(db: AsyncSession, usuario: Usuario, token: str | None) -> None:
    await db.execute(
        delete(Sessao).where(
            Sessao.id_usuario == usuario.id_usuario,
            Sessao.token_hash != hash_token(token or ""),
        )
    )


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


@router.post("/login", response_model=UsuarioOut | Requer2FAOut)
async def login(
    dados: LoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host
    agora = datetime.now(timezone.utc)

    if await esta_bloqueado(db, dados.email, ip, agora):
        raise _erro_bloqueio("Muitas tentativas de login. Tente novamente mais tarde.")

    usuario = await db.scalar(select(Usuario).where(Usuario.email == dados.email))
    hash_armazenado = usuario.senha_hash if usuario else None
    senha_valida = await verificar_senha(dados.senha, hash_armazenado)
    sucesso = usuario is not None and senha_valida

    if not sucesso:
        await registrar_tentativa(db, dados.email, ip, False, agora)
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")

    if usuario.dois_fatores:
        token, token_hash = gerar_token()
        db.add(
            Desafio2FA(
                id_usuario=usuario.id_usuario,
                token_hash=token_hash,
                expira_em=agora + timedelta(minutes=settings.DESAFIO_2FA_MIN),
                lembrar=dados.lembrar,
            )
        )
        await db.commit()
        response.set_cookie(
            key=COOKIE_DESAFIO,
            value=token,
            max_age=settings.DESAFIO_2FA_MIN * 60,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            path=CAMINHO_COOKIE_DESAFIO,
        )
        return Requer2FAOut()

    await registrar_tentativa(db, dados.email, ip, True, agora)
    await _criar_sessao(db, response, usuario, agora, dados.lembrar)
    return usuario


@router.post("/login/2fa", response_model=UsuarioOut)
async def login_2fa(
    dados: CodigoIn,
    request: Request,
    response: Response,
    token_desafio: str | None = Cookie(default=None, alias=COOKIE_DESAFIO),
    db: AsyncSession = Depends(get_db),
):
    if not token_desafio:
        raise DESAFIO_INVALIDO

    agora = datetime.now(timezone.utc)
    desafio = await db.scalar(
        select(Desafio2FA).where(
            Desafio2FA.token_hash == hash_token(token_desafio),
            Desafio2FA.expira_em > agora,
        )
    )
    if desafio is None:
        raise DESAFIO_INVALIDO

    usuario = await db.get(Usuario, desafio.id_usuario)
    ip = request.client.host

    if await esta_bloqueado(db, usuario.email, ip, agora):
        raise _erro_bloqueio("Muitas tentativas de login. Tente novamente mais tarde.")

    codigo_valido = await verificar_segundo_fator(db, usuario, dados.codigo, agora)
    await registrar_tentativa(db, usuario.email, ip, codigo_valido, agora)
    if not codigo_valido:
        raise HTTPException(status_code=401, detail="Código inválido.")

    consumido = await db.execute(
        delete(Desafio2FA).where(Desafio2FA.id_desafio_2fa == desafio.id_desafio_2fa)
    )
    if consumido.rowcount != 1:
        raise DESAFIO_INVALIDO
    await _criar_sessao(db, response, usuario, agora, desafio.lembrar)
    response.delete_cookie(
        key=COOKIE_DESAFIO,
        path=CAMINHO_COOKIE_DESAFIO,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
    return usuario


@router.get("/me", response_model=UsuarioOut)
async def me(usuario: Usuario = Depends(get_usuario_atual)):
    return usuario


@router.patch("/me", response_model=UsuarioOut, dependencies=[Depends(verificar_csrf)])
async def editar_me(
    dados: UsuarioUpdate,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    usuario.nome = dados.nome
    await db.commit()
    await db.refresh(usuario)
    return usuario


@router.post("/logout", status_code=204, dependencies=[Depends(verificar_csrf)])
async def logout(
    response: Response,
    token: str | None = Cookie(default=None, alias="sessao"),
    db: AsyncSession = Depends(get_db),
):
    if token:
        await db.execute(delete(Sessao).where(Sessao.token_hash == hash_token(token)))
        await db.commit()

    _apagar_cookie(response)


@router.post("/trocar-senha", response_model=MensagemOut, dependencies=[Depends(verificar_csrf)])
async def trocar_senha(
    dados: TrocaSenhaIn,
    request: Request,
    usuario: Usuario = Depends(get_usuario_atual),
    token: str | None = Cookie(default=None, alias="sessao"),
    db: AsyncSession = Depends(get_db),
):
    await _confirmar_senha(db, usuario, dados.senha_atual, request, "Senha atual incorreta.")

    usuario.senha_hash = await gerar_hash(dados.senha_nova)
    await _apagar_outras_sessoes(db, usuario, token)
    await db.commit()
    return MensagemOut(mensagem="Senha alterada com sucesso.")


@router.post("/excluir-conta", status_code=204, dependencies=[Depends(verificar_csrf)])
async def excluir_conta(
    dados: ExcluirContaIn,
    request: Request,
    response: Response,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    await _confirmar_senha(db, usuario, dados.senha, request, "Senha incorreta.")

    await db.delete(usuario)
    await db.commit()
    _apagar_cookie(response)


@router.get("/csrf", response_model=CSRFTokenOut, dependencies=[Depends(get_usuario_atual)])
async def obter_csrf(
    response: Response,
    token: str | None = Cookie(default=None, alias="sessao"),
):
    response.headers["Cache-Control"] = "no-store"
    csrf_token = gerar_csrf(token)
    return {"csrf_token": csrf_token}
    

@router.post("/2fa/iniciar", response_model=Iniciar2FAOut, dependencies=[Depends(verificar_csrf)])
async def iniciar_2fa(
    response: Response,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    if usuario.dois_fatores:
        raise HTTPException(status_code=409, detail="A verificação em duas etapas já está ativa.")

    segredo = gerar_segredo()
    usuario.totp_segredo = cifrar(segredo)
    usuario.totp_ultimo_passo = None
    await db.commit()

    response.headers["Cache-Control"] = "no-store"
    return Iniciar2FAOut(segredo=segredo, uri=gerar_uri(segredo, usuario.email))


@router.post("/2fa/ativar", response_model=CodigosRecuperacaoOut, dependencies=[Depends(verificar_csrf)])
async def ativar_2fa(
    dados: SenhaECodigoIn,
    request: Request,
    response: Response,
    usuario: Usuario = Depends(get_usuario_atual),
    token: str | None = Cookie(default=None, alias="sessao"),
    db: AsyncSession = Depends(get_db),
):
    if usuario.dois_fatores:
        raise HTTPException(status_code=409, detail="A verificação em duas etapas já está ativa.")
    if usuario.totp_segredo is None:
        raise HTTPException(status_code=409, detail="Inicie a configuração antes de ativar.")

    await _confirmar_senha(
        db, usuario, dados.senha, request, SENHA_OU_CODIGO_INCORRETOS, dados.codigo, so_totp=True
    )

    usuario.totp_ativado_em = datetime.now(timezone.utc)
    codigos = await substituir_codigos_recuperacao(db, usuario)
    await _apagar_outras_sessoes(db, usuario, token)
    await db.commit()

    response.headers["Cache-Control"] = "no-store"
    return CodigosRecuperacaoOut(codigos=codigos)


@router.post("/2fa/desativar", response_model=MensagemOut, dependencies=[Depends(verificar_csrf)])
async def desativar_2fa(
    dados: SenhaECodigoIn,
    request: Request,
    usuario: Usuario = Depends(get_usuario_atual),
    token: str | None = Cookie(default=None, alias="sessao"),
    db: AsyncSession = Depends(get_db),
):
    if not usuario.dois_fatores:
        raise HTTPException(status_code=409, detail="A verificação em duas etapas não está ativa.")

    await _confirmar_senha(db, usuario, dados.senha, request, SENHA_OU_CODIGO_INCORRETOS, dados.codigo)

    usuario.totp_segredo = None
    usuario.totp_ativado_em = None
    usuario.totp_ultimo_passo = None
    await db.execute(
        delete(CodigoRecuperacao).where(CodigoRecuperacao.id_usuario == usuario.id_usuario)
    )
    await db.execute(delete(Desafio2FA).where(Desafio2FA.id_usuario == usuario.id_usuario))
    await _apagar_outras_sessoes(db, usuario, token)
    await db.commit()
    return MensagemOut(mensagem="Verificação em duas etapas desativada.")


@router.post(
    "/2fa/codigos-recuperacao",
    response_model=CodigosRecuperacaoOut,
    dependencies=[Depends(verificar_csrf)],
)
async def gerar_novos_codigos_recuperacao(
    dados: SenhaECodigoIn,
    request: Request,
    response: Response,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    if not usuario.dois_fatores:
        raise HTTPException(status_code=409, detail="A verificação em duas etapas não está ativa.")

    await _confirmar_senha(db, usuario, dados.senha, request, SENHA_OU_CODIGO_INCORRETOS, dados.codigo)

    codigos = await substituir_codigos_recuperacao(db, usuario)
    await db.commit()

    response.headers["Cache-Control"] = "no-store"
    return CodigosRecuperacaoOut(codigos=codigos)
