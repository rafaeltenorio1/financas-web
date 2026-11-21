from sqlalchemy import select

from apoio import SENHA_PADRAO, cadastrar, criar_cliente, login, obter_csrf

NOVA_SENHA = "nova-senha-456"


async def _trocar(client, atual=SENHA_PADRAO, nova=NOVA_SENHA, csrf=None):
    if csrf is None:
        csrf = await obter_csrf(client)
    return await client.post(
        "/auth/trocar-senha",
        json={"senha_atual": atual, "senha_nova": nova},
        headers={"X-CSRF-Token": csrf},
    )


async def test_troca_senha_e_derruba_as_outras_sessoes(client, db):
    from models.sessao import Sessao
    from utils.security import hash_token

    await cadastrar(client)
    await login(client)

    async with criar_cliente() as outro_navegador:
        await login(outro_navegador)

        resposta = await _trocar(client)
        assert resposta.status_code == 200

        # A sessão de quem trocou continua; a outra foi encerrada.
        assert (await client.get("/auth/me")).status_code == 200
        assert (await outro_navegador.get("/auth/me")).status_code == 401

    sessoes = (await db.scalars(select(Sessao))).all()
    assert [s.token_hash for s in sessoes] == [hash_token(client.cookies["sessao"])]


async def test_depois_da_troca_so_a_senha_nova_funciona(logado):
    assert (await _trocar(logado)).status_code == 200

    async with criar_cliente() as novo:
        assert (await login(novo, senha=SENHA_PADRAO)).status_code == 401
        assert (await login(novo, senha=NOVA_SENHA)).status_code == 200


async def test_senha_atual_errada_e_recusada(logado):
    resposta = await _trocar(logado, atual="senha-errada-1")
    assert resposta.status_code == 401


async def test_troca_conta_como_tentativa_e_bloqueia(logado):
    from utils.config import settings

    csrf = await obter_csrf(logado)
    for _ in range(settings.LOGIN_MAX_FALHAS):
        await _trocar(logado, atual="senha-errada-1", csrf=csrf)

    resposta = await _trocar(logado, csrf=csrf)
    assert resposta.status_code == 429


async def test_troca_exige_csrf(logado):
    resposta = await logado.post(
        "/auth/trocar-senha", json={"senha_atual": SENHA_PADRAO, "senha_nova": NOVA_SENHA}
    )
    assert resposta.status_code == 403


async def test_troca_exige_login(client):
    resposta = await client.post(
        "/auth/trocar-senha",
        json={"senha_atual": SENHA_PADRAO, "senha_nova": NOVA_SENHA},
        headers={"X-CSRF-Token": "qualquer"},
    )
    # Sem cookie, o CSRF já falha antes de checar a sessão.
    assert resposta.status_code in (401, 403)


async def test_senha_nova_curta_e_recusada(logado):
    resposta = await _trocar(logado, nova="curta")
    assert resposta.status_code == 422
