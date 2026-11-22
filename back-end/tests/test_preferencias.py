import pytest

from apoio import obter_csrf


async def _editar(client, corpo):
    csrf = await obter_csrf(client)
    return await client.patch("/auth/me", json=corpo, headers={"X-CSRF-Token": csrf})


async def test_padroes_do_cadastro(logado):
    dados = (await logado.get("/auth/me")).json()

    assert dados["fuso"] == "America/Sao_Paulo"
    assert dados["lembrete_dias_antes"] == 1
    assert dados["lembrete_no_dia"] is True
    assert dados["lembrete_atraso"] is True
    assert dados["resumo_mensal"] is True


async def test_edita_preferencias_sem_mexer_no_nome(logado):
    resposta = await _editar(
        logado,
        {
            "fuso": "America/Manaus",
            "lembrete_dias_antes": 3,
            "lembrete_no_dia": False,
            "lembrete_atraso": False,
            "resumo_mensal": False,
        },
    )

    assert resposta.status_code == 200
    dados = (await logado.get("/auth/me")).json()
    assert dados["nome"] == "Ana"
    assert dados["fuso"] == "America/Manaus"
    assert dados["lembrete_dias_antes"] == 3
    assert dados["lembrete_no_dia"] is False
    assert dados["lembrete_atraso"] is False
    assert dados["resumo_mensal"] is False


async def test_editar_nome_nao_mexe_nas_preferencias(logado):
    await _editar(logado, {"lembrete_dias_antes": 0})
    await _editar(logado, {"nome": "Ana Maria"})

    dados = (await logado.get("/auth/me")).json()
    assert dados["nome"] == "Ana Maria"
    assert dados["lembrete_dias_antes"] == 0


async def test_corpo_vazio_nao_altera_nada(logado):
    antes = (await logado.get("/auth/me")).json()

    resposta = await _editar(logado, {})

    assert resposta.status_code == 200
    assert resposta.json() == antes


async def test_fuso_inexistente_responde_422(logado):
    resposta = await _editar(logado, {"fuso": "Lua/Base_Tranquilidade"})

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Fuso horário inválido."
    assert (await logado.get("/auth/me")).json()["fuso"] == "America/Sao_Paulo"


@pytest.mark.parametrize(
    "corpo",
    [
        {"lembrete_dias_antes": 8},
        {"lembrete_dias_antes": -1},
        {"lembrete_dias_antes": None},
        {"fuso": None},
        {"fuso": ""},
        {"lembrete_no_dia": None},
        {"resumo_mensal": None},
    ],
)
async def test_valores_invalidos_respondem_422(logado, corpo):
    assert (await _editar(logado, corpo)).status_code == 422
