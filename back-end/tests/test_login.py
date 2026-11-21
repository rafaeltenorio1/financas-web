from sqlalchemy import select

from apoio import cadastrar, login


async def test_login_cria_sessao_e_cookie_seguro(client, db):
    from models.sessao import Sessao
    from utils.security import hash_token

    await cadastrar(client)
    resposta = await login(client)

    assert resposta.status_code == 200
    assert resposta.json()["email"] == "ana@example.com"

    set_cookie = resposta.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie

    token = client.cookies["sessao"]
    sessoes = (await db.scalars(select(Sessao))).all()
    assert len(sessoes) == 1
    # O banco guarda só o hash do token, nunca o valor do cookie.
    assert sessoes[0].token_hash == hash_token(token)
    assert sessoes[0].token_hash != token


async def test_login_aceita_email_com_maiusculas(client):
    await cadastrar(client, email="ana@example.com")
    resposta = await login(client, email="  ANA@example.com")
    assert resposta.status_code == 200


async def test_senha_errada_e_email_inexistente_tem_mesma_resposta(client):
    await cadastrar(client)

    senha_errada = await login(client, senha="senha-errada-1")
    email_inexistente = await login(client, email="ninguem@example.com")

    assert senha_errada.status_code == email_inexistente.status_code == 401
    assert senha_errada.json() == email_inexistente.json()
    assert "sessao" not in client.cookies


async def test_me_retorna_usuario_logado(logado):
    resposta = await logado.get("/auth/me")
    assert resposta.status_code == 200
    assert resposta.json()["email"] == "ana@example.com"


async def test_me_sem_cookie_retorna_401(client):
    resposta = await client.get("/auth/me")
    assert resposta.status_code == 401


async def test_me_com_token_inventado_retorna_401(client):
    client.cookies.set("sessao", "token-que-nao-existe")
    resposta = await client.get("/auth/me")
    assert resposta.status_code == 401


async def test_login_registra_tentativas(client, db):
    from models.log_tentativa import LogTentativa

    await cadastrar(client)
    await login(client, senha="senha-errada-1")
    await login(client)

    tentativas = (
        await db.scalars(select(LogTentativa).order_by(LogTentativa.ocorrida_em))
    ).all()
    assert [t.sucesso for t in tentativas] == [False, True]
    assert all(t.email_tentativa == "ana@example.com" for t in tentativas)
