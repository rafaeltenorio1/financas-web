from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from apoio import cadastrar, corpo_html, corpo_texto, criar_cliente, login, obter_csrf


async def _verificar(client, token):
    return await client.post("/auth/verificar-email", json={"token": token})


async def _reenviar(client):
    csrf = await obter_csrf(client)
    return await client.post("/auth/verificar-email/reenviar", headers={"X-CSRF-Token": csrf})


async def _envelhecer_tokens(db, minutos):
    from models.token_email import TokenEmail

    atras = timedelta(minutes=minutos)
    await db.execute(
        update(TokenEmail).values(
            criado_em=TokenEmail.criado_em - atras, expira_em=TokenEmail.expira_em - atras
        )
    )
    await db.commit()


async def test_cadastro_envia_link_de_verificacao(client, caixa, db):
    from models.token_email import TokenEmail
    from utils.config import settings
    from utils.security import hash_token

    await cadastrar(client)

    mensagens = await caixa.recebidos()
    assert [m["Subject"] for m in mensagens] == ["Confirme seu e-mail"]
    assert mensagens[0]["To"] == "ana@example.com"
    token = await caixa.token_enviado("ana@example.com")
    link = f"{settings.FRONT_URL}/#/verificar-email?token={token}"
    assert link in corpo_texto(mensagens[0])
    assert f'href="{link}"' in corpo_html(mensagens[0])

    guardado = await db.scalar(select(TokenEmail.token_hash))
    assert guardado == hash_token(token)
    assert guardado != token


async def test_link_verifica_o_email(client, caixa):
    await cadastrar(client)
    token = await caixa.token_enviado("ana@example.com")

    async with criar_cliente() as outro_navegador:
        resposta = await _verificar(outro_navegador, token)

    assert resposta.status_code == 200
    assert (await login(client)).json()["email_verificado"] is True


async def test_link_so_pode_ser_usado_uma_vez(client, caixa):
    await cadastrar(client)
    token = await caixa.token_enviado("ana@example.com")

    assert (await _verificar(client, token)).status_code == 200
    resposta = await _verificar(client, token)

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Link inválido ou expirado."


async def test_link_vencido_nao_vale(client, caixa, db):
    from utils.config import settings

    await cadastrar(client)
    token = await caixa.token_enviado("ana@example.com")
    await _envelhecer_tokens(db, settings.TOKEN_VERIFICACAO_HORAS * 60 + 1)

    assert (await _verificar(client, token)).status_code == 400


async def test_token_invalido_ou_de_outra_finalidade_nao_vale(client, caixa):
    await cadastrar(client)
    await client.post("/auth/esqueci-senha", json={"email": "ana@example.com"})
    token_redefinicao = await caixa.token_enviado("ana@example.com")

    assert (await _verificar(client, "token-inventado")).status_code == 400
    assert (await _verificar(client, token_redefinicao)).status_code == 400


async def test_get_nao_verifica(client, caixa):
    await cadastrar(client)
    token = await caixa.token_enviado("ana@example.com")

    resposta = await client.get(f"/auth/verificar-email?token={token}")

    assert resposta.status_code == 405


async def test_reenviar_respeita_o_intervalo(logado, caixa, db):
    from utils.config import settings

    await caixa.esvaziar()

    resposta = await _reenviar(logado)
    assert resposta.status_code == 429
    assert resposta.headers["retry-after"] == str(settings.TOKEN_INTERVALO_ENVIO_MIN * 60)
    assert await caixa.recebidos() == []

    await _envelhecer_tokens(db, settings.TOKEN_INTERVALO_ENVIO_MIN)
    resposta = await _reenviar(logado)
    assert resposta.status_code == 202
    assert await caixa.assuntos() == ["Confirme seu e-mail"]


async def test_reenviar_invalida_o_link_anterior(logado, caixa, db):
    from utils.config import settings

    antigo = await caixa.token_enviado("ana@example.com")
    await _envelhecer_tokens(db, settings.TOKEN_INTERVALO_ENVIO_MIN)
    assert (await _reenviar(logado)).status_code == 202
    novo = await caixa.token_enviado("ana@example.com")

    assert novo != antigo
    assert (await _verificar(logado, antigo)).status_code == 400
    assert (await _verificar(logado, novo)).status_code == 200


async def test_reenviar_com_email_ja_verificado_responde_409(logado, caixa):
    token = await caixa.token_enviado("ana@example.com")
    await _verificar(logado, token)

    assert (await _reenviar(logado)).status_code == 409


async def test_reenviar_exige_sessao(client):
    resposta = await client.post("/auth/verificar-email/reenviar")
    assert resposta.status_code in (401, 403)


async def test_verificar_exige_origem_permitida(client, caixa):
    await cadastrar(client)
    token = await caixa.token_enviado("ana@example.com")

    async with criar_cliente(origem="http://site-malicioso.example") as atacante:
        resposta = await _verificar(atacante, token)

    assert resposta.status_code == 403
