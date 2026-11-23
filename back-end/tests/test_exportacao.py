import csv
import io

import pytest

from apoio import ORIGEM_FRONT, cadastrar, criar_cliente, login, obter_csrf

URL = "/transacoes/exportar"
CABECALHO = [
    "Data",
    "Tipo",
    "Nome",
    "Categoria",
    "Valor",
    "Forma de pagamento",
    "Descrição",
    "Conta recorrente",
]


async def _post(client, url, corpo=None):
    csrf = await obter_csrf(client)
    resposta = await client.post(url, json=corpo, headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


async def _transacao(client, **campos):
    corpo = {"valor": "100.00", "tipo": "despesa", "data_hora": "2026-11-10T12:00:00Z", **campos}
    return await _post(client, "/transacoes", corpo)


async def _exportar(client, **params):
    resposta = await client.get(URL, params=params)
    assert resposta.status_code == 200, resposta.text
    return resposta


def _linhas(resposta):
    texto = resposta.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(texto, newline=""), delimiter=";"))


async def test_arquivo_pronto_para_o_excel(logado):
    resposta = await _exportar(logado)

    assert resposta.headers["content-type"] == "text/csv; charset=utf-8"
    assert resposta.headers["cache-control"] == "no-store"
    disposicao = resposta.headers["content-disposition"]
    assert disposicao.startswith('attachment; filename="financas-transacoes-')
    assert disposicao.endswith('.csv"')
    assert resposta.content.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in resposta.content
    assert _linhas(resposta) == [CABECALHO]


async def test_linha_com_formato_brasileiro(logado):
    categoria = await _post(logado, "/categorias", {"nome": "Farmácia Ação", "tipo_padrao": "despesa"})
    await _transacao(
        logado,
        nome="Remédios",
        valor="1234.50",
        data_hora="2026-11-22T12:00:00Z",
        id_categoria=categoria["id_categoria"],
        forma_pagamento="cartao de credito",
        descricao="Pressão e vitaminas",
    )

    linhas = _linhas(await _exportar(logado))

    assert linhas[1] == [
        "22/11/2026 09:00",
        "despesa",
        "Remédios",
        "Farmácia Ação",
        "1234,50",
        "cartao de credito",
        "Pressão e vitaminas",
        "",
    ]
    assert "Remédios".encode("utf-8") in (await _exportar(logado)).content


async def test_data_no_fuso_do_usuario(logado):
    csrf = await obter_csrf(logado)
    await logado.patch("/auth/me", json={"fuso": "Asia/Tokyo"}, headers={"X-CSRF-Token": csrf})
    await _transacao(logado, data_hora="2026-11-22T20:30:00Z")

    assert _linhas(await _exportar(logado))[1][0] == "23/11/2026 05:30"


async def test_ordem_cronologica(logado):
    await _transacao(logado, nome="Depois", data_hora="2026-11-20T12:00:00Z")
    await _transacao(logado, nome="Antes", data_hora="2026-11-01T12:00:00Z")

    nomes = [linha[2] for linha in _linhas(await _exportar(logado))[1:]]

    assert nomes == ["Antes", "Depois"]


async def test_filtros_iguais_aos_da_listagem(logado):
    categoria = await _post(logado, "/categorias", {"nome": "Só esta", "tipo_padrao": "despesa"})
    await _transacao(logado, nome="Outubro", data_hora="2026-10-15T12:00:00Z")
    await _transacao(logado, nome="Salário", tipo="receita", data_hora="2026-11-05T12:00:00Z")
    await _transacao(logado, nome="Com categoria", id_categoria=categoria["id_categoria"])

    async def nomes(**params):
        return [linha[2] for linha in _linhas(await _exportar(logado, **params))[1:]]

    assert await nomes(tipo="receita") == ["Salário"]
    assert await nomes(id_categoria=categoria["id_categoria"]) == ["Com categoria"]
    assert await nomes(
        data_inicio="2026-11-01T00:00:00Z", data_fim="2026-12-01T00:00:00Z"
    ) == ["Salário", "Com categoria"]


async def test_nao_exporta_transacoes_de_outro_usuario(logado):
    await _transacao(logado, nome="Da Ana")
    async with criar_cliente() as bia:
        await cadastrar(bia, email="bia@example.com", nome="Bia")
        await login(bia, email="bia@example.com")
        await _transacao(bia, nome="Da Bia")

        nomes_bia = [linha[2] for linha in _linhas(await _exportar(bia))[1:]]

    nomes_ana = [linha[2] for linha in _linhas(await _exportar(logado))[1:]]
    assert nomes_ana == ["Da Ana"]
    assert nomes_bia == ["Da Bia"]


async def test_mostra_a_conta_recorrente_que_gerou_o_pagamento(logado):
    conta = await _post(
        logado,
        "/contas-recorrentes",
        {
            "nome": "Aluguel",
            "valor": "1500.00",
            "tipo": "despesa",
            "periodicidade": "mensal",
            "data_inicio": "2026-12-10",
        },
    )
    await _post(logado, f"/contas-recorrentes/{conta['id_conta_recorrente']}/pagar")

    linha = _linhas(await _exportar(logado))[1]

    assert linha[2] == "Aluguel"
    assert linha[7] == "Aluguel"


@pytest.mark.parametrize(
    "nome, esperado",
    [
        ("=HYPERLINK(\"http://malicioso.example\")", "'=HYPERLINK(\"http://malicioso.example\")"),
        ("+55 conta", "'+55 conta"),
        ("-50", "'-50"),
        ("@SOMA(A1)", "'@SOMA(A1)"),
        ("\tTab", "'\tTab"),
        ("Mercado = barato", "Mercado = barato"),
    ],
)
async def test_neutraliza_formulas_nos_textos(logado, nome, esperado):
    await _transacao(logado, nome=nome, descricao=nome)

    linha = _linhas(await _exportar(logado))[1]

    assert linha[2] == esperado
    assert linha[6] == esperado
    assert linha[4] == "100,00"


async def test_separador_e_quebra_de_linha_dentro_do_campo(logado):
    descricao = 'Parcela 1; ver "nota"\nsegunda linha'
    await _transacao(logado, nome="Compra", descricao=descricao)

    linhas = _linhas(await _exportar(logado))

    assert len(linhas) == 2
    assert linhas[1][6] == descricao


async def test_front_consegue_ler_o_nome_do_arquivo(logado):
    resposta = await logado.get(URL, headers={"Origin": ORIGEM_FRONT})

    expostos = resposta.headers["access-control-expose-headers"].lower()
    assert "content-disposition" in expostos


async def test_exige_login(client):
    assert (await client.get(URL)).status_code == 401


async def test_nao_confunde_com_busca_por_id(logado):
    resposta = await logado.get(URL)
    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/csv")


async def test_exportacao_respeita_a_busca(logado):
    await _transacao(logado, nome="Farmácia do bairro")
    await _transacao(logado, nome="Mercado")

    linhas = _linhas(await _exportar(logado, busca="farmacia"))

    assert len(linhas) == 2
    assert "Farmácia do bairro" in linhas[1]
