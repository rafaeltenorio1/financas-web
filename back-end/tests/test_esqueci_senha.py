from datetime import timedelta

import pyotp
from sqlalchemy import update

from apoio import SENHA_PADRAO, cadastrar, corpo_texto, criar_cliente, login, obter_csrf

MENSAGEM_GENERICA = "Se o e-mail estiver cadastrado, enviaremos um link para redefinir a senha."
SENHA_NOVA = "senha-nova-789"


async def _pedir(client, email="ana@example.com"):
    return await client.post("/auth/esqueci-senha", json={"email": email})


async def _redefinir(client, token, senha=SENHA_NOVA):
    return await client.post("/auth/redefinir-senha", json={"token": token, "senha_nova": senha})


async def _token_de_redefinicao(client, caixa, email="ana@example.com"):
    await caixa.esvaziar()
    assert (await _pedir(client, email)).status_code == 202
    return await caixa.token_enviado(email)


async def _envelhecer_tokens(db, minutos):
    from models.token_email import TokenEmail

    atras = timedelta(minutes=minutos)
    await db.execute(
        update(TokenEmail).values(
            criado_em=TokenEmail.criado_em - atras, expira_em=TokenEmail.expira_em - atras
        )
    )
    await db.commit()


async def test_envia_link_para_email_cadastrado(client, caixa):
    from utils.config import settings

    await cadastrar(client)
    await caixa.esvaziar()

    resposta = await _pedir(client)

    assert resposta.status_code == 202
    assert resposta.json() == {"mensagem": MENSAGEM_GENERICA}
    assert await caixa.assuntos() == ["Redefinição de senha"]
    token = await caixa.token_enviado("ana@example.com")
    assert f"{settings.FRONT_URL}/#/redefinir-senha?token={token}" in corpo_texto(caixa.mensagens[0])


async def test_email_inexistente_tem_a_mesma_resposta_e_nao_envia_nada(client, caixa):
    resposta = await _pedir(client, "ninguem@example.com")

    assert resposta.status_code == 202
    assert resposta.json() == {"mensagem": MENSAGEM_GENERICA}
    assert await caixa.recebidos() == []


async def test_pedidos_seguidos_nao_enchem_a_caixa(client, caixa):
    await cadastrar(client)
    await caixa.esvaziar()

    for _ in range(5):
        resposta = await _pedir(client)
        assert resposta.status_code == 202
        assert resposta.json() == {"mensagem": MENSAGEM_GENERICA}

    assert await caixa.assuntos() == ["Redefinição de senha"]


async def test_redefinir_troca_a_senha_e_encerra_todas_as_sessoes(logado, caixa):
    async with criar_cliente() as outro:
        token = await _token_de_redefinicao(outro, caixa)
        resposta = await _redefinir(outro, token)

    assert resposta.status_code == 200
    assert (await logado.get("/auth/me")).status_code == 401
    assert (await login(logado)).status_code == 401
    assert (await login(logado, senha=SENHA_NOVA)).status_code == 200


async def test_redefinir_verifica_o_email_e_avisa(client, caixa):
    await cadastrar(client)
    token = await _token_de_redefinicao(client, caixa)
    await caixa.esvaziar()

    assert (await _redefinir(client, token)).status_code == 200

    assert await caixa.assuntos() == ["Sua senha foi redefinida"]
    assert (await login(client, senha=SENHA_NOVA)).json()["email_verificado"] is True


async def test_link_de_redefinicao_so_vale_uma_vez(client, caixa):
    await cadastrar(client)
    token = await _token_de_redefinicao(client, caixa)

    assert (await _redefinir(client, token)).status_code == 200
    resposta = await _redefinir(client, token, senha="mais-uma-senha-1")

    assert resposta.status_code == 400
    assert (await login(client, senha=SENHA_NOVA)).status_code == 200


async def test_link_de_redefinicao_vencido_nao_vale(client, caixa, db):
    from utils.config import settings

    await cadastrar(client)
    token = await _token_de_redefinicao(client, caixa)
    await _envelhecer_tokens(db, settings.TOKEN_REDEFINIR_SENHA_MIN + 1)

    assert (await _redefinir(client, token)).status_code == 400
    assert (await login(client)).status_code == 200


async def test_senha_curta_nao_consome_o_link(client, caixa):
    await cadastrar(client)
    token = await _token_de_redefinicao(client, caixa)

    assert (await _redefinir(client, token, senha="curta")).status_code == 422
    assert (await _redefinir(client, token)).status_code == 200


async def test_token_de_verificacao_nao_redefine_senha(client, caixa):
    await cadastrar(client)
    token_verificacao = await caixa.token_enviado("ana@example.com")

    assert (await _redefinir(client, token_verificacao)).status_code == 400


async def test_redefinir_libera_o_bloqueio_por_tentativas(client, caixa):
    from utils.config import settings

    await cadastrar(client)
    for _ in range(settings.LOGIN_MAX_FALHAS):
        await login(client, senha="senha-errada-1")
    assert (await login(client)).status_code == 429

    token = await _token_de_redefinicao(client, caixa)
    assert (await _redefinir(client, token)).status_code == 200

    assert (await login(client, senha=SENHA_NOVA)).status_code == 200


async def test_redefinir_nao_desliga_o_2fa(logado, caixa, db):
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

    token = await _token_de_redefinicao(logado, caixa)
    assert (await _redefinir(logado, token)).status_code == 200

    resposta = await login(logado, senha=SENHA_NOVA)
    assert resposta.json() == {"requer_2fa": True}
