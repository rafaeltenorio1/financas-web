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


# --- Preferências do painel ------------------------------------------------

PAINEL = {
    "cartoes": [
        {"id": "saldo", "largura": "estreito"},
        {"id": "transacoes", "largura": "largo"},
        {"id": "contas", "largura": "inteiro"},
    ],
    "numeros": ["previsao", "credito", "media12"],
    "periodo_meses": 12,
    "lista_transacoes": "lista",
}


async def test_painel_comeca_sem_preferencias(logado):
    assert (await logado.get("/auth/me")).json()["preferencias_painel"] is None


async def test_salva_e_le_as_preferencias_do_painel(logado):
    resposta = await _editar(logado, {"preferencias_painel": PAINEL})

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["preferencias_painel"] == PAINEL
    assert (await logado.get("/auth/me")).json()["preferencias_painel"] == PAINEL


async def test_salvar_painel_nao_mexe_no_resto(logado):
    await _editar(logado, {"lembrete_dias_antes": 5})
    await _editar(logado, {"preferencias_painel": PAINEL})

    dados = (await logado.get("/auth/me")).json()
    assert dados["lembrete_dias_antes"] == 5
    assert dados["nome"] == "Ana"


async def test_editar_outro_campo_nao_apaga_o_painel(logado):
    await _editar(logado, {"preferencias_painel": PAINEL})
    await _editar(logado, {"nome": "Ana Maria"})

    assert (await logado.get("/auth/me")).json()["preferencias_painel"] == PAINEL


async def test_nulo_volta_ao_painel_padrao(logado):
    await _editar(logado, {"preferencias_painel": PAINEL})
    resposta = await _editar(logado, {"preferencias_painel": None})

    assert resposta.status_code == 200
    assert (await logado.get("/auth/me")).json()["preferencias_painel"] is None


async def test_painel_vazio_e_aceito(logado):
    vazio = {"cartoes": [], "numeros": [], "periodo_meses": 3, "lista_transacoes": "colunas"}
    resposta = await _editar(logado, {"preferencias_painel": vazio})

    assert resposta.status_code == 200
    assert resposta.json()["preferencias_painel"] == vazio


def _com(**mudancas):
    return {**PAINEL, **mudancas}


@pytest.mark.parametrize(
    "painel",
    [
        _com(cartoes=[{"id": "grafico_hack", "largura": "largo"}]),
        _com(cartoes=[{"id": "saldo", "largura": "gigante"}]),
        _com(cartoes=[{"id": "saldo", "largura": "largo"}, {"id": "saldo", "largura": "estreito"}]),
        _com(cartoes=[{"id": "saldo", "largura": "largo", "cor": "red"}]),
        _com(numeros=["previsao", "previsao"]),
        _com(numeros=["senha"]),
        _com(periodo_meses=6),
        _com(lista_transacoes="tabela"),
        _com(extra="nao"),
        {k: v for k, v in PAINEL.items() if k != "numeros"},
        "texto",
        [],
    ],
)
async def test_painel_invalido_responde_422(logado, painel):
    resposta = await _editar(logado, {"preferencias_painel": painel})

    assert resposta.status_code == 422
    assert (await logado.get("/auth/me")).json()["preferencias_painel"] is None


async def test_painel_grande_demais_responde_422(logado):
    numeros = ["previsao", "pagar", "media", "credito", "fixos", "maior", "guardado", "quantidade", "assinaturas", "media12", "previsao"]
    resposta = await _editar(logado, {"preferencias_painel": _com(numeros=numeros)})

    assert resposta.status_code == 422


async def test_salvar_painel_exige_csrf(logado):
    resposta = await logado.patch("/auth/me", json={"preferencias_painel": PAINEL})

    assert resposta.status_code == 403
    assert (await logado.get("/auth/me")).json()["preferencias_painel"] is None
