from decimal import Decimal

import pytest
from sqlalchemy import select

from apoio import cadastrar, criar_cliente, login, obter_csrf

BASE = "/contas-recorrentes"


async def _criar(client, esperado=201, **campos):
    corpo = {
        "nome": "Aluguel",
        "valor": "1500.00",
        "tipo": "despesa",
        "periodicidade": "mensal",
        "data_inicio": "2026-12-10",
        **campos,
    }
    csrf = await obter_csrf(client)
    resposta = await client.post(BASE, json=corpo, headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == esperado, resposta.text
    return resposta.json()


async def _post(client, url, corpo=None):
    csrf = await obter_csrf(client)
    if corpo is None:
        return await client.post(url, headers={"X-CSRF-Token": csrf})
    return await client.post(url, json=corpo, headers={"X-CSRF-Token": csrf})


async def _patch(client, id_conta, corpo):
    csrf = await obter_csrf(client)
    return await client.patch(f"{BASE}/{id_conta}", json=corpo, headers={"X-CSRF-Token": csrf})


@pytest.fixture
async def outro_usuario():
    async with criar_cliente() as bia:
        await cadastrar(bia, email="bia@example.com", nome="Bia")
        assert (await login(bia, email="bia@example.com")).status_code == 200
        yield bia


async def test_cria_conta_com_proximo_vencimento_no_inicio(logado):
    conta = await _criar(logado, forma_pagamento="boleto")

    assert conta["nome"] == "Aluguel"
    assert Decimal(conta["valor"]) == Decimal("1500.00")
    assert conta["periodicidade"] == "mensal"
    assert conta["proximo_vencimento"] == "2026-12-10"
    assert conta["ativa"] is True
    assert conta["avisar"] is True
    assert conta["forma_pagamento"] == "boleto"
    assert "id_usuario" not in conta


@pytest.mark.parametrize(
    "campos",
    [
        {"valor": "0"},
        {"valor": "-10"},
        {"nome": "   "},
        {"periodicidade": "diaria"},
        {"data_inicio": "2026-12-10", "data_fim": "2026-12-09"},
        {"tipo": "outro"},
    ],
)
async def test_criar_valida_os_dados(logado, campos):
    await _criar(logado, esperado=422, **campos)


async def test_aceita_categoria_padrao_e_recusa_categoria_alheia(logado, outro_usuario, db):
    from models.categoria import Categoria

    padrao = await db.scalar(select(Categoria.id_categoria).where(Categoria.id_usuario.is_(None)).limit(1))
    conta = await _criar(logado, id_categoria=str(padrao))
    assert conta["id_categoria"] == str(padrao)

    csrf = await obter_csrf(outro_usuario)
    alheia = (
        await outro_usuario.post(
            "/categorias", json={"nome": "Só da Bia", "tipo_padrao": "despesa"}, headers={"X-CSRF-Token": csrf}
        )
    ).json()["id_categoria"]
    await _criar(logado, esperado=422, id_categoria=alheia)


async def test_lista_so_as_proprias_em_ordem_de_vencimento(logado, outro_usuario):
    await _criar(logado, nome="Internet", data_inicio="2026-12-15")
    await _criar(logado, nome="Aluguel", data_inicio="2026-12-05")
    await _criar(outro_usuario, nome="Da Bia")

    nomes = [c["nome"] for c in (await logado.get(BASE)).json()]

    assert nomes == ["Aluguel", "Internet"]


async def test_filtros_da_listagem(logado):
    await _criar(logado, nome="Aluguel", data_inicio="2026-12-05")
    await _criar(logado, nome="Salário", tipo="receita", data_inicio="2026-12-01")
    inativa = await _criar(logado, nome="Academia", data_inicio="2026-12-20")
    await _patch(logado, inativa["id_conta_recorrente"], {"ativa": False})

    async def nomes(params):
        return [c["nome"] for c in (await logado.get(BASE, params=params)).json()]

    assert await nomes({"tipo": "receita"}) == ["Salário"]
    assert await nomes({"ativa": "false"}) == ["Academia"]
    assert await nomes({"vence_ate": "2026-12-05"}) == ["Salário", "Aluguel"]


async def test_conta_de_outro_usuario_responde_404(logado, outro_usuario):
    conta = await _criar(outro_usuario)
    url = f"{BASE}/{conta['id_conta_recorrente']}"

    assert (await logado.get(url)).status_code == 404
    assert (await _patch(logado, conta["id_conta_recorrente"], {"valor": "1"})).status_code == 404
    assert (await _post(logado, f"{url}/pagar")).status_code == 404
    assert (await _post(logado, f"{url}/pular")).status_code == 404
    csrf = await obter_csrf(logado)
    assert (await logado.delete(url, headers={"X-CSRF-Token": csrf})).status_code == 404
    assert (await outro_usuario.get(url)).status_code == 200


async def test_pagar_cria_transacao_ligada_e_avanca_o_vencimento(logado):
    conta = await _criar(logado, forma_pagamento="pix")

    resposta = await _post(logado, f"{BASE}/{conta['id_conta_recorrente']}/pagar")

    assert resposta.status_code == 201, resposta.text
    dados = resposta.json()
    transacao = dados["transacao"]
    assert transacao["nome"] == "Aluguel"
    assert Decimal(transacao["valor"]) == Decimal("1500.00")
    assert transacao["tipo"] == "despesa"
    assert transacao["forma_pagamento"] == "pix"
    assert transacao["id_conta_recorrente"] == conta["id_conta_recorrente"]
    assert dados["conta"]["proximo_vencimento"] == "2027-01-10"

    lista = (await logado.get("/transacoes")).json()
    assert [t["id_transacao"] for t in lista] == [transacao["id_transacao"]]


async def test_pagar_aceita_valor_data_e_forma_diferentes(logado):
    conta = await _criar(logado, nome="Luz", valor="200.00", forma_pagamento="boleto")

    resposta = await _post(
        logado,
        f"{BASE}/{conta['id_conta_recorrente']}/pagar",
        {
            "valor": "187.43",
            "data_hora": "2026-12-09T15:30:00-03:00",
            "forma_pagamento": "pix",
            "descricao": "Conta de dezembro",
        },
    )

    transacao = resposta.json()["transacao"]
    assert Decimal(transacao["valor"]) == Decimal("187.43")
    assert transacao["data_hora"].startswith("2026-12-09T18:30:00")
    assert transacao["forma_pagamento"] == "pix"
    assert transacao["descricao"] == "Conta de dezembro"


async def test_pagar_com_valor_invalido_nao_avanca(logado):
    conta = await _criar(logado)
    url = f"{BASE}/{conta['id_conta_recorrente']}"

    assert (await _post(logado, f"{url}/pagar", {"valor": "0"})).status_code == 422
    assert (await logado.get(url)).json()["proximo_vencimento"] == "2026-12-10"


async def test_pagamentos_seguidos_respeitam_o_dia_original(logado):
    conta = await _criar(logado, data_inicio="2027-01-31")
    url = f"{BASE}/{conta['id_conta_recorrente']}/pagar"

    vencimentos = []
    for _ in range(3):
        vencimentos.append((await _post(logado, url)).json()["conta"]["proximo_vencimento"])

    assert vencimentos == ["2027-02-28", "2027-03-31", "2027-04-30"]


async def test_conta_termina_depois_do_ultimo_pagamento(logado):
    conta = await _criar(logado, data_inicio="2026-12-10", data_fim="2027-01-10")
    url = f"{BASE}/{conta['id_conta_recorrente']}"

    assert (await _post(logado, f"{url}/pagar")).json()["conta"]["ativa"] is True
    ultima = (await _post(logado, f"{url}/pagar")).json()["conta"]
    assert ultima["ativa"] is False

    resposta = await _post(logado, f"{url}/pagar")
    assert resposta.status_code == 409
    assert (await _post(logado, f"{url}/pular")).status_code == 409


async def test_pular_avanca_sem_criar_transacao(logado):
    conta = await _criar(logado, periodicidade="semanal")

    resposta = await _post(logado, f"{BASE}/{conta['id_conta_recorrente']}/pular")

    assert resposta.status_code == 200
    assert resposta.json()["proximo_vencimento"] == "2026-12-17"
    assert (await logado.get("/transacoes")).json() == []


async def test_editar_conta(logado):
    conta = await _criar(logado)

    resposta = await _patch(
        logado,
        conta["id_conta_recorrente"],
        {"valor": "1600.00", "avisar": False, "proximo_vencimento": "2027-02-10"},
    )

    assert resposta.status_code == 200
    dados = resposta.json()
    assert Decimal(dados["valor"]) == Decimal("1600.00")
    assert dados["avisar"] is False
    assert dados["proximo_vencimento"] == "2027-02-10"
    assert dados["periodicidade"] == "mensal"


@pytest.mark.parametrize(
    "corpo",
    [
        {"proximo_vencimento": "2026-12-09"},
        {"data_fim": "2026-12-01"},
        {"valor": None},
        {"nome": None},
        {"ativa": None},
    ],
)
async def test_editar_recusa_estado_invalido(logado, corpo):
    conta = await _criar(logado)
    assert (await _patch(logado, conta["id_conta_recorrente"], corpo)).status_code == 422


async def test_reativar_conta_que_ja_terminou_responde_422(logado):
    conta = await _criar(logado, data_inicio="2026-12-10", data_fim="2026-12-10")
    await _post(logado, f"{BASE}/{conta['id_conta_recorrente']}/pagar")

    resposta = await _patch(logado, conta["id_conta_recorrente"], {"ativa": True})

    assert resposta.status_code == 422


async def test_apagar_conta_mantem_as_transacoes(logado):
    conta = await _criar(logado)
    url = f"{BASE}/{conta['id_conta_recorrente']}"
    transacao = (await _post(logado, f"{url}/pagar")).json()["transacao"]

    csrf = await obter_csrf(logado)
    assert (await logado.delete(url, headers={"X-CSRF-Token": csrf})).status_code == 204

    assert (await logado.get(url)).status_code == 404
    restante = (await logado.get(f"/transacoes/{transacao['id_transacao']}")).json()
    assert restante["id_conta_recorrente"] is None


async def test_alteracoes_exigem_csrf(logado):
    conta = await _criar(logado)

    resposta = await logado.post(f"{BASE}/{conta['id_conta_recorrente']}/pagar")

    assert resposta.status_code == 403


async def test_exige_login(client):
    assert (await client.get(BASE)).status_code == 401


async def test_icone_comeca_nulo(logado):
    assert (await _criar(logado))["icone"] is None


@pytest.mark.parametrize("icone", ["m-netflix", "c-moradia", "m-" + "a" * 38])
async def test_cria_com_icone_de_marca_ou_generico(logado, icone):
    assert (await _criar(logado, icone=icone))["icone"] == icone


@pytest.mark.parametrize(
    "icone",
    ["netflix", "x-netflix", "m-", "M-netflix", "m-Netflix", "m-net_flix", "m-net flix", "m-" + "a" * 39, 'm-a"><svg', ""],
)
async def test_icone_invalido_retorna_422(logado, icone):
    await _criar(logado, esperado=422, icone=icone)


async def test_editar_icone_null_volta_ao_automatico_e_omitir_mantem(logado):
    conta = await _criar(logado, icone="m-netflix")
    id_conta = conta["id_conta_recorrente"]

    resposta = await _patch(logado, id_conta, {"valor": "40.00"})
    assert resposta.json()["icone"] == "m-netflix"

    resposta = await _patch(logado, id_conta, {"icone": "m-spotify"})
    assert resposta.json()["icone"] == "m-spotify"

    resposta = await _patch(logado, id_conta, {"icone": None})
    assert resposta.status_code == 200
    assert resposta.json()["icone"] is None


async def test_banco_recusa_icone_fora_do_formato(logado, db):
    from datetime import date

    from sqlalchemy.exc import IntegrityError

    from models.conta_recorrente import ContaRecorrente
    from models.enums import Periodicidade, TipoTransacao
    from models.usuario import Usuario

    usuario = await db.scalar(select(Usuario).limit(1))
    db.add(
        ContaRecorrente(
            id_usuario=usuario.id_usuario,
            nome="Direto no banco",
            valor=Decimal("10.00"),
            tipo=TipoTransacao.DESPESA,
            periodicidade=Periodicidade.MENSAL,
            data_inicio=date(2026, 12, 1),
            proximo_vencimento=date(2026, 12, 1),
            icone="Netflix",
        )
    )
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()
