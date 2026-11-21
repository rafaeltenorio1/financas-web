from apoio import cadastrar, criar_cliente, login, obter_csrf


async def test_csrf_exige_login(client):
    assert (await client.get("/auth/csrf")).status_code == 401


async def test_csrf_nao_vai_para_cache(logado):
    resposta = await logado.get("/auth/csrf")
    assert resposta.headers["cache-control"] == "no-store"


async def test_logout_sem_token_csrf_e_recusado(logado):
    resposta = await logado.post("/auth/logout")
    assert resposta.status_code == 403
    assert (await logado.get("/auth/me")).status_code == 200


async def test_logout_com_token_csrf_errado_e_recusado(logado):
    resposta = await logado.post("/auth/logout", headers={"X-CSRF-Token": "a" * 64})
    assert resposta.status_code == 403


async def test_logout_com_csrf_valido_encerra_sessao(logado, db):
    from sqlalchemy import select

    from models.sessao import Sessao

    csrf = await obter_csrf(logado)
    resposta = await logado.post("/auth/logout", headers={"X-CSRF-Token": csrf})

    assert resposta.status_code == 204
    assert "sessao" not in logado.cookies
    assert (await db.scalars(select(Sessao))).all() == []


async def test_token_csrf_de_outra_sessao_nao_vale(client):
    await cadastrar(client)
    await login(client)

    async with criar_cliente() as outro_navegador:
        await login(outro_navegador)
        csrf_do_outro = await obter_csrf(outro_navegador)

    resposta = await client.post("/auth/logout", headers={"X-CSRF-Token": csrf_do_outro})
    assert resposta.status_code == 403


async def test_post_sem_origin_e_recusado():
    async with criar_cliente(origem=None) as sem_origin:
        resposta = await sem_origin.post(
            "/auth/register",
            json={"nome": "Ana", "email": "ana@example.com", "senha": "senha-forte-123"},
        )
    assert resposta.status_code == 403


async def test_post_de_origin_desconhecida_e_recusado():
    async with criar_cliente(origem="https://site-malicioso.example") as atacante:
        resposta = await atacante.post(
            "/auth/login", json={"email": "ana@example.com", "senha": "senha-forte-123"}
        )
    assert resposta.status_code == 403


async def test_get_nao_exige_origin(client):
    await cadastrar(client)
    await login(client)
    del client.headers["Origin"]

    assert (await client.get("/auth/me")).status_code == 200


async def test_cors_libera_so_a_origem_do_front(client):
    permitida = await client.options(
        "/auth/login",
        headers={"Access-Control-Request-Method": "POST"},
    )
    assert permitida.headers["access-control-allow-origin"] == client.headers["Origin"]
    assert permitida.headers["access-control-allow-credentials"] == "true"

    proibida = await client.options(
        "/auth/login",
        headers={
            "Origin": "https://site-malicioso.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in proibida.headers
