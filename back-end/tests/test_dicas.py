import asyncio

import pytest

from apoio import cadastrar, criar_cliente, login, obter_csrf


async def _marcar(client, id_dica, csrf=None):
    csrf = csrf or await obter_csrf(client)
    return await client.post("/auth/me/dicas", json={"id": id_dica}, headers={"X-CSRF-Token": csrf})


async def _dicas(client):
    return (await client.get("/auth/me")).json()["dicas_vistas"]


async def test_conta_nova_comeca_sem_dicas_vistas(logado):
    assert await _dicas(logado) == []


async def test_marca_dica_vista(logado):
    resposta = await _marcar(logado, "boas-vindas")

    assert resposta.status_code == 204
    assert await _dicas(logado) == ["boas-vindas"]


async def test_marcar_de_novo_nao_duplica(logado):
    await _marcar(logado, "boas-vindas")
    await _marcar(logado, "boas-vindas")
    await _marcar(logado, "busca")

    assert await _dicas(logado) == ["boas-vindas", "busca"]


async def test_marcar_ao_mesmo_tempo_nao_duplica(logado):
    csrf = await obter_csrf(logado)
    respostas = await asyncio.gather(*(_marcar(logado, "valor-centavos", csrf) for _ in range(5)))

    assert all(r.status_code == 204 for r in respostas)
    assert await _dicas(logado) == ["valor-centavos"]


@pytest.mark.parametrize("corpo", [{"id": "inventada"}, {"id": ""}, {}, {"id": "busca", "extra": 1}])
async def test_recusa_dica_fora_da_lista(logado, corpo):
    csrf = await obter_csrf(logado)
    resposta = await logado.post("/auth/me/dicas", json=corpo, headers={"X-CSRF-Token": csrf})

    assert resposta.status_code == 422
    assert await _dicas(logado) == []


async def test_exige_csrf(logado):
    resposta = await logado.post("/auth/me/dicas", json={"id": "busca"})

    assert resposta.status_code == 403
    assert await _dicas(logado) == []


async def test_exige_sessao(client):
    resposta = await client.post("/auth/me/dicas", json={"id": "busca"}, headers={"X-CSRF-Token": "x"})

    assert resposta.status_code in (401, 403)


async def test_recusa_origem_desconhecida(logado):
    csrf = await obter_csrf(logado)
    resposta = await logado.post(
        "/auth/me/dicas",
        json={"id": "busca"},
        headers={"X-CSRF-Token": csrf, "Origin": "https://atacante.example"},
    )

    assert resposta.status_code == 403
    assert await _dicas(logado) == []


async def test_dicas_de_um_usuario_nao_afetam_outro(logado):
    await _marcar(logado, "boas-vindas")

    async with criar_cliente() as outro:
        await cadastrar(outro, email="bia@example.com", nome="Bia")
        assert (await login(outro, email="bia@example.com")).status_code == 200
        assert await _dicas(outro) == []

    assert await _dicas(logado) == ["boas-vindas"]
