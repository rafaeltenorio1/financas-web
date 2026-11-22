import re
from datetime import datetime, timedelta, timezone

import pyotp
import pytest
from sqlalchemy import func, select, update

from apoio import SENHA_PADRAO, cadastrar, criar_cliente, login, obter_csrf

FORMATO_CODIGO_RECUPERACAO = re.compile(r"[A-Z2-7]{4}(-[A-Z2-7]{4}){3}")


async def _iniciar(client) -> str:
    csrf = await obter_csrf(client)
    resposta = await client.post("/auth/2fa/iniciar", headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["segredo"]


async def _ativar(client, segredo, senha=SENHA_PADRAO, codigo=None):
    csrf = await obter_csrf(client)
    return await client.post(
        "/auth/2fa/ativar",
        json={"senha": senha, "codigo": codigo or pyotp.TOTP(segredo).now()},
        headers={"X-CSRF-Token": csrf},
    )


async def _liberar_passo(db):
    from models.usuario import Usuario

    await db.execute(update(Usuario).values(totp_ultimo_passo=None))
    await db.commit()


@pytest.fixture
async def com_2fa(logado, db):
    segredo = await _iniciar(logado)
    resposta = await _ativar(logado, segredo)
    assert resposta.status_code == 200, resposta.text
    await _liberar_passo(db)
    return segredo, resposta.json()["codigos"]


async def _login_ate_desafio(client):
    resposta = await login(client)
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == {"requer_2fa": True}
    return resposta


async def test_iniciar_devolve_segredo_e_guarda_cifrado(logado, db):
    from models.usuario import Usuario
    from utils.totp import decifrar

    csrf = await obter_csrf(logado)
    resposta = await logado.post("/auth/2fa/iniciar", headers={"X-CSRF-Token": csrf})

    assert resposta.status_code == 200
    assert resposta.headers["cache-control"] == "no-store"
    dados = resposta.json()
    assert dados["uri"].startswith("otpauth://totp/")
    assert "issuer=Finan" in dados["uri"]

    usuario = await db.scalar(select(Usuario))
    assert usuario.totp_segredo != dados["segredo"]
    assert decifrar(usuario.totp_segredo) == dados["segredo"]
    assert usuario.totp_ativado_em is None
    assert (await logado.get("/auth/me")).json()["dois_fatores"] is False


async def test_iniciar_exige_login_e_csrf(client, logado):
    assert (await logado.post("/auth/2fa/iniciar")).status_code == 403

    async with criar_cliente() as anonimo:
        resposta = await anonimo.post("/auth/2fa/iniciar", headers={"X-CSRF-Token": "x"})
        assert resposta.status_code in (401, 403)


async def test_ativar_sem_iniciar_responde_409(logado):
    resposta = await _ativar(logado, None, codigo="123456")
    assert resposta.status_code == 409


async def test_ativar_com_codigo_errado_nao_liga(logado):
    segredo = await _iniciar(logado)
    codigo_certo = pyotp.TOTP(segredo).now()
    codigo_errado = f"{(int(codigo_certo) + 1) % 1_000_000:06d}"

    resposta = await _ativar(logado, segredo, codigo=codigo_errado)

    assert resposta.status_code == 401
    assert (await logado.get("/auth/me")).json()["dois_fatores"] is False


async def test_ativar_com_senha_errada_nao_liga(logado):
    segredo = await _iniciar(logado)

    resposta = await _ativar(logado, segredo, senha="senha-errada-1")

    assert resposta.status_code == 401
    assert (await logado.get("/auth/me")).json()["dois_fatores"] is False


async def test_ativar_liga_devolve_codigos_e_derruba_outras_sessoes(logado):
    async with criar_cliente() as outro_navegador:
        assert (await login(outro_navegador)).status_code == 200

        segredo = await _iniciar(logado)
        resposta = await _ativar(logado, segredo)

        assert resposta.status_code == 200, resposta.text
        assert resposta.headers["cache-control"] == "no-store"
        codigos = resposta.json()["codigos"]
        assert len(codigos) == 10
        assert len(set(codigos)) == 10
        assert all(FORMATO_CODIGO_RECUPERACAO.fullmatch(c) for c in codigos)

        assert (await logado.get("/auth/me")).json()["dois_fatores"] is True
        assert (await outro_navegador.get("/auth/me")).status_code == 401


async def test_codigos_de_recuperacao_ficam_so_como_hash(com_2fa, db):
    from models.codigo_recuperacao import CodigoRecuperacao

    _, codigos = com_2fa
    hashes = set(await db.scalars(select(CodigoRecuperacao.codigo_hash)))

    assert len(hashes) == 10
    assert not hashes & set(codigos)


async def test_iniciar_ou_ativar_de_novo_responde_409(com_2fa, logado):
    segredo, _ = com_2fa
    csrf = await obter_csrf(logado)

    assert (await logado.post("/auth/2fa/iniciar", headers={"X-CSRF-Token": csrf})).status_code == 409
    assert (await _ativar(logado, segredo)).status_code == 409


async def test_login_com_2fa_nao_cria_sessao_antes_do_codigo(com_2fa):
    async with criar_cliente() as navegador:
        resposta = await _login_ate_desafio(navegador)

        assert "sessao" not in resposta.cookies
        assert "desafio_2fa" in resposta.cookies
        assert (await navegador.get("/auth/me")).status_code == 401


async def test_login_2fa_com_codigo_certo_cria_sessao(com_2fa, db):
    from models.desafio_2fa import Desafio2FA

    segredo, _ = com_2fa
    async with criar_cliente() as navegador:
        await _login_ate_desafio(navegador)

        resposta = await navegador.post("/auth/login/2fa", json={"codigo": pyotp.TOTP(segredo).now()})

        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["email"] == "ana@example.com"
        assert (await navegador.get("/auth/me")).status_code == 200
        assert await db.scalar(select(func.count()).select_from(Desafio2FA)) == 0


async def test_desafio_so_pode_ser_usado_uma_vez(com_2fa, db):
    segredo, _ = com_2fa
    async with criar_cliente() as navegador:
        resposta = await _login_ate_desafio(navegador)
        token_desafio = resposta.cookies["desafio_2fa"]
        await navegador.post("/auth/login/2fa", json={"codigo": pyotp.TOTP(segredo).now()})

    await _liberar_passo(db)
    async with criar_cliente() as atacante:
        atacante.cookies.set("desafio_2fa", token_desafio, path="/auth/login")
        resposta = await atacante.post("/auth/login/2fa", json={"codigo": pyotp.TOTP(segredo).now()})
        assert resposta.status_code == 401


async def test_login_2fa_sem_desafio_ou_com_desafio_vencido(com_2fa, db):
    from models.desafio_2fa import Desafio2FA

    segredo, _ = com_2fa
    async with criar_cliente() as navegador:
        resposta = await navegador.post("/auth/login/2fa", json={"codigo": "123456"})
        assert resposta.status_code == 401

        await _login_ate_desafio(navegador)
        agora = datetime.now(timezone.utc)
        await db.execute(
            update(Desafio2FA).values(
                criado_em=agora - timedelta(minutes=10), expira_em=agora - timedelta(seconds=1)
            )
        )
        await db.commit()

        resposta = await navegador.post("/auth/login/2fa", json={"codigo": pyotp.TOTP(segredo).now()})
        assert resposta.status_code == 401


async def test_mesmo_codigo_totp_nao_vale_duas_vezes(com_2fa):
    segredo, _ = com_2fa
    codigo = pyotp.TOTP(segredo).now()

    async with criar_cliente() as primeiro:
        await _login_ate_desafio(primeiro)
        assert (await primeiro.post("/auth/login/2fa", json={"codigo": codigo})).status_code == 200

    async with criar_cliente() as segundo:
        await _login_ate_desafio(segundo)
        assert (await segundo.post("/auth/login/2fa", json={"codigo": codigo})).status_code == 401


async def test_codigos_errados_bloqueiam_mesmo_com_senha_certa_a_cada_vez(com_2fa):
    from utils.config import settings

    async with criar_cliente() as atacante:
        for _ in range(settings.LOGIN_MAX_FALHAS):
            await _login_ate_desafio(atacante)
            resposta = await atacante.post("/auth/login/2fa", json={"codigo": "000000"})
            assert resposta.status_code == 401

        assert (await login(atacante)).status_code == 429


async def test_codigo_de_recuperacao_entra_uma_vez_so(com_2fa):
    _, codigos = com_2fa
    digitado = codigos[0].lower().replace("-", " ")

    async with criar_cliente() as navegador:
        await _login_ate_desafio(navegador)
        resposta = await navegador.post("/auth/login/2fa", json={"codigo": digitado})
        assert resposta.status_code == 200, resposta.text

    async with criar_cliente() as navegador:
        await _login_ate_desafio(navegador)
        resposta = await navegador.post("/auth/login/2fa", json={"codigo": codigos[0]})
        assert resposta.status_code == 401


async def test_desativar_exige_senha_e_codigo_e_volta_ao_login_simples(com_2fa, logado, db):
    from models.codigo_recuperacao import CodigoRecuperacao

    segredo, _ = com_2fa
    csrf = await obter_csrf(logado)

    resposta = await logado.post(
        "/auth/2fa/desativar",
        json={"senha": "senha-errada-1", "codigo": pyotp.TOTP(segredo).now()},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 401

    resposta = await logado.post(
        "/auth/2fa/desativar",
        json={"senha": SENHA_PADRAO, "codigo": pyotp.TOTP(segredo).now()},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 200, resposta.text
    assert (await logado.get("/auth/me")).json()["dois_fatores"] is False
    assert await db.scalar(select(func.count()).select_from(CodigoRecuperacao)) == 0

    async with criar_cliente() as navegador:
        resposta = await login(navegador)
        assert resposta.status_code == 200
        assert resposta.json()["email"] == "ana@example.com"


async def test_desativar_sem_2fa_responde_409(logado):
    csrf = await obter_csrf(logado)
    resposta = await logado.post(
        "/auth/2fa/desativar",
        json={"senha": SENHA_PADRAO, "codigo": "123456"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 409


async def test_gerar_novos_codigos_invalida_os_antigos(com_2fa, logado):
    segredo, antigos = com_2fa
    csrf = await obter_csrf(logado)

    resposta = await logado.post(
        "/auth/2fa/codigos-recuperacao",
        json={"senha": SENHA_PADRAO, "codigo": pyotp.TOTP(segredo).now()},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 200, resposta.text
    novos = resposta.json()["codigos"]
    assert not set(novos) & set(antigos)

    async with criar_cliente() as navegador:
        await _login_ate_desafio(navegador)
        assert (await navegador.post("/auth/login/2fa", json={"codigo": antigos[0]})).status_code == 401
        assert (await navegador.post("/auth/login/2fa", json={"codigo": novos[0]})).status_code == 200


async def test_login_sem_2fa_continua_direto(client):
    await cadastrar(client)
    resposta = await login(client)

    assert resposta.status_code == 200
    assert resposta.json()["dois_fatores"] is False
    assert "sessao" in resposta.cookies


async def test_limpeza_apaga_desafios_vencidos(com_2fa, db):
    from models.desafio_2fa import Desafio2FA
    from utils.limpeza import limpar_dados_vencidos

    async with criar_cliente() as navegador:
        await _login_ate_desafio(navegador)

    agora = datetime.now(timezone.utc)
    _, _, desafios, _ = await limpar_dados_vencidos(db, agora)
    assert desafios == 0

    _, _, desafios, _ = await limpar_dados_vencidos(db, agora + timedelta(minutes=10))
    assert desafios == 1
    assert await db.scalar(select(func.count()).select_from(Desafio2FA)) == 0
