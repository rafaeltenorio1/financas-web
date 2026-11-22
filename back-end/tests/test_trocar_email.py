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

NOVO = "ana.nova@example.com"
MENSAGEM_GENERICA = "Se o endereço estiver disponível, enviaremos um link de confirmação para ele."


async def _pedir(client, email_novo=NOVO, senha=SENHA_PADRAO, codigo=None):
    dados = {"senha": senha, "email_novo": email_novo}
    if codigo is not None:
        dados["codigo"] = codigo
    csrf = await obter_csrf(client)
    return await client.post("/auth/trocar-email", json=dados, headers={"X-CSRF-Token": csrf})


async def _confirmar(client, token):
    return await client.post("/auth/trocar-email/confirmar", json={"token": token})


@pytest.fixture
async def logado(logado, caixa):
    await marcar_verificado()
    await caixa.esvaziar()
    return logado


async def test_pedido_envia_link_ao_novo_e_aviso_ao_antigo(logado, caixa):
    from utils.config import settings

    resposta = await _pedir(logado)

    assert resposta.status_code == 202
    assert resposta.json() == {"mensagem": MENSAGEM_GENERICA}
    mensagens = {m["To"]: m for m in await caixa.recebidos()}
    assert set(mensagens) == {NOVO, "ana@example.com"}
    assert mensagens[NOVO]["Subject"] == "Confirme seu novo e-mail"
    assert mensagens["ana@example.com"]["Subject"] == "Pedido de troca de e-mail"
    assert "a***@example.com" in corpo_texto(mensagens["ana@example.com"])
    assert NOVO not in corpo_texto(mensagens["ana@example.com"])
    token = await caixa.token_enviado(NOVO)
    assert f"{settings.FRONT_URL}/#/confirmar-email?token={token}" in corpo_texto(mensagens[NOVO])


async def test_email_so_muda_depois_da_confirmacao(logado, caixa):
    await _pedir(logado)
    assert (await logado.get("/auth/me")).json()["email"] == "ana@example.com"

    token = await caixa.token_enviado(NOVO)
    await caixa.esvaziar()
    resposta = await _confirmar(logado, token)

    assert resposta.status_code == 200
    dados = (await logado.get("/auth/me")).json()
    assert dados["email"] == NOVO
    assert dados["email_verificado"] is True
    mensagens = await caixa.recebidos()
    assert [(m["To"], m["Subject"]) for m in mensagens] == [
        ("ana@example.com", "O e-mail da sua conta foi trocado")
    ]


async def test_depois_da_troca_o_login_usa_o_novo_email(logado, caixa):
    await _pedir(logado)
    await _confirmar(logado, await caixa.token_enviado(NOVO))

    async with criar_cliente() as outro:
        assert (await login(outro)).status_code == 401
        assert (await login(outro, email=NOVO)).status_code == 200


async def test_confirmar_encerra_as_outras_sessoes_e_mantem_a_atual(logado, caixa):
    async with criar_cliente() as outro:
        assert (await login(outro)).status_code == 200
        await _pedir(logado)
        await _confirmar(logado, await caixa.token_enviado(NOVO))

        assert (await outro.get("/auth/me")).status_code == 401
    assert (await logado.get("/auth/me")).status_code == 200


async def test_senha_errada_nao_envia_nada(logado, caixa):
    resposta = await _pedir(logado, senha="senha-errada-1")

    assert resposta.status_code == 401
    assert await caixa.recebidos() == []


async def test_email_em_uso_tem_a_mesma_resposta_e_nao_envia_nada(logado, caixa):
    async with criar_cliente() as outro:
        await cadastrar(outro, email=NOVO, nome="Outra")
    await caixa.esvaziar()

    resposta = await _pedir(logado)

    assert resposta.status_code == 202
    assert resposta.json() == {"mensagem": MENSAGEM_GENERICA}
    assert await caixa.recebidos() == []


async def test_email_ocupado_antes_da_confirmacao_responde_409(logado, caixa):
    await _pedir(logado)
    token = await caixa.token_enviado(NOVO)
    async with criar_cliente() as outro:
        await cadastrar(outro, email=NOVO, nome="Outra")

    resposta = await _confirmar(logado, token)

    assert resposta.status_code == 409
    assert (await logado.get("/auth/me")).json()["email"] == "ana@example.com"


async def test_novo_email_igual_ao_atual_responde_400(logado):
    resposta = await _pedir(logado, email_novo="ANA@example.com")
    assert resposta.status_code == 400


async def test_sem_email_verificado_o_antigo_nao_recebe_aviso(client, caixa):
    await cadastrar(client)
    await login(client)
    await caixa.esvaziar()

    assert (await _pedir(client)).status_code == 202

    assert [m["To"] for m in await caixa.recebidos()] == [NOVO]


async def test_troca_invalida_links_pendentes_do_email_antigo(client, caixa):
    await cadastrar(client)
    await login(client)
    token_verificacao = await caixa.token_enviado("ana@example.com")

    await _pedir(client)
    assert (await _confirmar(client, await caixa.token_enviado(NOVO))).status_code == 200

    resposta = await client.post("/auth/verificar-email", json={"token": token_verificacao})
    assert resposta.status_code == 400


async def test_link_de_troca_so_vale_uma_vez(logado, caixa):
    await _pedir(logado)
    token = await caixa.token_enviado(NOVO)

    assert (await _confirmar(logado, token)).status_code == 200
    assert (await _confirmar(logado, token)).status_code == 400


async def test_com_2fa_exige_o_codigo(logado, caixa, db):
    from models.usuario import Usuario

    csrf = await obter_csrf(logado)
    segredo = (await logado.post("/auth/2fa/iniciar", headers={"X-CSRF-Token": csrf})).json()[
        "segredo"
    ]
    csrf = await obter_csrf(logado)
    ativacao = await logado.post(
        "/auth/2fa/ativar",
        json={"senha": SENHA_PADRAO, "codigo": pyotp.TOTP(segredo).now()},
        headers={"X-CSRF-Token": csrf},
    )
    assert ativacao.status_code == 200
    await db.execute(update(Usuario).values(totp_ultimo_passo=None))
    await db.commit()
    await caixa.esvaziar()

    sem_codigo = await _pedir(logado)
    assert sem_codigo.status_code == 400
    assert await caixa.recebidos() == []

    com_codigo = await _pedir(logado, codigo=pyotp.TOTP(segredo).now())
    assert com_codigo.status_code == 202
    assert NOVO in [m["To"] for m in await caixa.recebidos()]


async def test_pedido_exige_csrf(logado):
    resposta = await logado.post(
        "/auth/trocar-email", json={"senha": SENHA_PADRAO, "email_novo": NOVO}
    )
    assert resposta.status_code == 403
