import pyotp
import pytest
from sqlalchemy import update

from apoio import (
    SENHA_PADRAO,
    cadastrar,
    corpo_texto,
    criar_cliente,
    login,
    marcar_verificado,
    obter_csrf,
)


async def _post_csrf(client, url, dados):
    csrf = await obter_csrf(client)
    return await client.post(url, json=dados, headers={"X-CSRF-Token": csrf})


async def _liberar_passo(db):
    from models.usuario import Usuario

    await db.execute(update(Usuario).values(totp_ultimo_passo=None))
    await db.commit()


@pytest.fixture
async def logado(logado, caixa):
    await marcar_verificado()
    await caixa.esvaziar()
    return logado


async def _cadastrar_verificado(client, caixa, email="ana@example.com"):
    await cadastrar(client, email=email)
    await marcar_verificado(email)
    await caixa.esvaziar()


@pytest.fixture
async def com_2fa(logado, db, caixa):
    csrf = await obter_csrf(logado)
    segredo = (await logado.post("/auth/2fa/iniciar", headers={"X-CSRF-Token": csrf})).json()[
        "segredo"
    ]
    resposta = await _post_csrf(
        logado, "/auth/2fa/ativar", {"senha": SENHA_PADRAO, "codigo": pyotp.TOTP(segredo).now()}
    )
    assert resposta.status_code == 200, resposta.text
    await _liberar_passo(db)
    await caixa.esvaziar()
    return segredo


async def test_login_nao_envia_email(client, caixa):
    await _cadastrar_verificado(client, caixa)
    assert (await login(client)).status_code == 200

    assert await caixa.recebidos() == []


async def test_alerta_nao_vai_para_email_nao_verificado(client, caixa):
    await cadastrar(client)
    await login(client)
    await caixa.esvaziar()

    resposta = await _post_csrf(
        client,
        "/auth/trocar-senha",
        {"senha_atual": SENHA_PADRAO, "senha_nova": "outra-senha-456"},
    )
    assert resposta.status_code == 200

    assert await caixa.recebidos() == []


async def test_trocar_senha_avisa_por_email(logado, caixa):
    resposta = await _post_csrf(
        logado,
        "/auth/trocar-senha",
        {"senha_atual": SENHA_PADRAO, "senha_nova": "outra-senha-456"},
    )
    assert resposta.status_code == 200

    mensagens = await caixa.recebidos()
    assert len(mensagens) == 1
    assert mensagens[0]["To"] == "ana@example.com"
    assert mensagens[0]["Subject"] == "Sua senha foi alterada"
    assert "Olá, Ana." in corpo_texto(mensagens[0])


async def test_trocar_senha_com_senha_errada_nao_avisa(logado, caixa):
    resposta = await _post_csrf(
        logado,
        "/auth/trocar-senha",
        {"senha_atual": "senha-errada-1", "senha_nova": "outra-senha-456"},
    )
    assert resposta.status_code == 401

    assert await caixa.recebidos() == []


async def test_ativar_2fa_avisa_por_email(logado, caixa):
    csrf = await obter_csrf(logado)
    segredo = (await logado.post("/auth/2fa/iniciar", headers={"X-CSRF-Token": csrf})).json()[
        "segredo"
    ]
    assert await caixa.recebidos() == []

    resposta = await _post_csrf(
        logado, "/auth/2fa/ativar", {"senha": SENHA_PADRAO, "codigo": pyotp.TOTP(segredo).now()}
    )
    assert resposta.status_code == 200

    assert await caixa.assuntos() == ["Verificação em duas etapas ativada"]


async def test_desativar_2fa_avisa_por_email(logado, com_2fa, caixa):
    resposta = await _post_csrf(
        logado,
        "/auth/2fa/desativar",
        {"senha": SENHA_PADRAO, "codigo": pyotp.TOTP(com_2fa).now()},
    )
    assert resposta.status_code == 200

    assert await caixa.assuntos() == ["Verificação em duas etapas desativada"]


async def test_novos_codigos_de_recuperacao_avisam_por_email(logado, com_2fa, caixa):
    resposta = await _post_csrf(
        logado,
        "/auth/2fa/codigos-recuperacao",
        {"senha": SENHA_PADRAO, "codigo": pyotp.TOTP(com_2fa).now()},
    )
    assert resposta.status_code == 200

    assert await caixa.assuntos() == ["Novos códigos de recuperação"]


async def test_excluir_conta_avisa_por_email(logado, caixa):
    resposta = await _post_csrf(logado, "/auth/excluir-conta", {"senha": SENHA_PADRAO})
    assert resposta.status_code == 204

    mensagens = await caixa.recebidos()
    assert [m["Subject"] for m in mensagens] == ["Sua conta foi excluída"]
    assert mensagens[0]["To"] == "ana@example.com"


async def test_bloqueio_no_login_avisa_uma_vez_so(client, caixa):
    from utils.config import settings

    await _cadastrar_verificado(client, caixa)
    for _ in range(settings.LOGIN_MAX_FALHAS - 1):
        assert (await login(client, senha="senha-errada-1")).status_code == 401
    assert await caixa.recebidos() == []

    assert (await login(client, senha="senha-errada-1")).status_code == 401
    for _ in range(3):
        assert (await login(client, senha="senha-errada-1")).status_code == 429

    assert await caixa.assuntos() == ["Tentativas de acesso bloqueadas"]


async def test_bloqueio_de_email_inexistente_nao_envia_nada(client, caixa):
    from utils.config import settings

    for _ in range(settings.LOGIN_MAX_FALHAS + 1):
        await login(client, email="ninguem@example.com", senha="senha-errada-1")

    assert await caixa.recebidos() == []


async def test_bloqueio_por_ip_nao_avisa_os_donos_dos_emails(client, caixa, monkeypatch):
    from utils.config import settings

    monkeypatch.setattr(settings, "LOGIN_MAX_FALHAS_IP", 3)
    for i in range(4):
        await _cadastrar_verificado(client, caixa, email=f"pessoa{i}@example.com")
    for i in range(3):
        assert (await login(client, email=f"pessoa{i}@example.com", senha="senha-errada-1")).status_code == 401

    assert (await login(client, email="pessoa3@example.com", senha="senha-errada-1")).status_code == 429
    assert await caixa.recebidos() == []


async def test_bloqueio_por_falhas_em_rota_autenticada_avisa(logado, caixa):
    from utils.config import settings

    for _ in range(settings.LOGIN_MAX_FALHAS):
        resposta = await _post_csrf(
            logado,
            "/auth/trocar-senha",
            {"senha_atual": "senha-errada-1", "senha_nova": "outra-senha-456"},
        )
        assert resposta.status_code == 401

    assert await caixa.assuntos() == ["Tentativas de acesso bloqueadas"]


async def test_bloqueio_no_codigo_2fa_avisa(client, com_2fa, caixa):
    from utils.config import settings

    for _ in range(settings.LOGIN_MAX_FALHAS):
        async with criar_cliente() as outro:
            assert (await login(outro)).json() == {"requer_2fa": True}
            resposta = await outro.post("/auth/login/2fa", json={"codigo": "000000"})
            assert resposta.status_code == 401

    assert await caixa.assuntos() == ["Tentativas de acesso bloqueadas"]
