import pytest
from sqlalchemy import func, select

from apoio import SENHA_PADRAO, cadastrar, criar_cliente, login, obter_csrf


@pytest.fixture
async def csrf(logado):
    return await obter_csrf(logado)


async def _editar(client, csrf, corpo):
    return await client.patch("/auth/me", json=corpo, headers={"X-CSRF-Token": csrf})


async def _excluir(client, csrf, senha=SENHA_PADRAO):
    return await client.post(
        "/auth/excluir-conta", json={"senha": senha}, headers={"X-CSRF-Token": csrf}
    )


async def _contar(db, model, *filtros):
    return await db.scalar(select(func.count()).select_from(model).where(*filtros))


async def test_edita_nome(logado, csrf):
    resposta = await _editar(logado, csrf, {"nome": "  Ana Maria  "})

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Ana Maria"
    assert (await logado.get("/auth/me")).json()["nome"] == "Ana Maria"


@pytest.mark.parametrize("corpo", [{"nome": ""}, {"nome": "   "}, {"nome": "x" * 256}, {"nome": None}])
async def test_editar_nome_invalido(logado, csrf, corpo):
    assert (await _editar(logado, csrf, corpo)).status_code == 422


async def test_editar_nao_altera_email(logado, csrf):
    resposta = await _editar(logado, csrf, {"nome": "Ana", "email": "outro@example.com"})

    assert resposta.status_code == 200
    assert resposta.json()["email"] == "ana@example.com"


async def test_editar_exige_csrf(logado):
    resposta = await logado.patch("/auth/me", json={"nome": "Ana Maria"})
    assert resposta.status_code == 403


async def test_editar_exige_login(client):
    resposta = await client.patch(
        "/auth/me", json={"nome": "Ana"}, headers={"X-CSRF-Token": "qualquer"}
    )
    assert resposta.status_code in (401, 403)


async def test_cadastro_rejeita_nome_so_com_espacos(client):
    resposta = await client.post(
        "/auth/register",
        json={"nome": "   ", "email": "ana@example.com", "senha": SENHA_PADRAO},
    )
    assert resposta.status_code == 422


async def test_excluir_apaga_tudo_do_usuario(logado, csrf, db):
    from models.categoria import Categoria
    from models.sessao import Sessao
    from models.transacao import Transacao
    from models.usuario import Usuario

    await logado.post(
        "/categorias", json={"nome": "Pet"}, headers={"X-CSRF-Token": csrf}
    )
    await logado.post(
        "/transacoes",
        json={"valor": "10.00", "tipo": "despesa", "data_hora": "2026-11-05T12:00:00-03:00"},
        headers={"X-CSRF-Token": csrf},
    )
    async with criar_cliente() as outro_navegador:
        await login(outro_navegador)

        resposta = await _excluir(logado, csrf)
        assert resposta.status_code == 204
        assert resposta.content == b""
        assert "sessao" not in logado.cookies

        assert (await outro_navegador.get("/auth/me")).status_code == 401

    assert await _contar(db, Usuario) == 0
    assert await _contar(db, Sessao) == 0
    assert await _contar(db, Transacao) == 0
    assert await _contar(db, Categoria, Categoria.id_usuario.is_not(None)) == 0
    assert await _contar(db, Categoria, Categoria.id_usuario.is_(None)) > 0


async def test_excluir_nao_afeta_outros_usuarios(logado, csrf, db):
    from models.usuario import Usuario

    async with criar_cliente() as bia:
        await cadastrar(bia, email="bia@example.com", nome="Bia")
        await login(bia, email="bia@example.com")

        assert (await _excluir(logado, csrf)).status_code == 204
        assert (await bia.get("/auth/me")).status_code == 200

    assert await _contar(db, Usuario) == 1


async def test_depois_de_excluir_nao_faz_login_e_pode_recadastrar(logado, csrf):
    await _excluir(logado, csrf)

    async with criar_cliente() as novo:
        assert (await login(novo)).status_code == 401
        await cadastrar(novo)


async def test_excluir_com_senha_errada_nao_apaga(logado, csrf, db):
    from models.usuario import Usuario

    resposta = await _excluir(logado, csrf, senha="senha-errada-1")

    assert resposta.status_code == 401
    assert await _contar(db, Usuario) == 1
    assert (await logado.get("/auth/me")).status_code == 200


async def test_excluir_conta_como_tentativa_e_bloqueia(logado, csrf, db):
    from models.usuario import Usuario
    from utils.config import settings

    for _ in range(settings.LOGIN_MAX_FALHAS):
        assert (await _excluir(logado, csrf, senha="senha-errada-1")).status_code == 401

    resposta = await _excluir(logado, csrf)

    assert resposta.status_code == 429
    assert await _contar(db, Usuario) == 1


async def test_excluir_mantem_log_de_tentativas(logado, csrf, db):
    from models.log_tentativa import LogTentativa

    await _excluir(logado, csrf, senha="senha-errada-1")
    await _excluir(logado, csrf)

    registros = await _contar(db, LogTentativa, LogTentativa.email_tentativa == "ana@example.com")
    assert registros >= 3


async def test_excluir_exige_csrf(logado, db):
    from models.usuario import Usuario

    resposta = await logado.post("/auth/excluir-conta", json={"senha": SENHA_PADRAO})

    assert resposta.status_code == 403
    assert await _contar(db, Usuario) == 1


async def test_excluir_exige_login(client):
    resposta = await client.post(
        "/auth/excluir-conta",
        json={"senha": SENHA_PADRAO},
        headers={"X-CSRF-Token": "qualquer"},
    )
    assert resposta.status_code in (401, 403)


async def test_excluir_sem_senha_e_recusado(logado, csrf):
    resposta = await logado.post(
        "/auth/excluir-conta", json={}, headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 422
