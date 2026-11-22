import base64
from decimal import Decimal

import pytest
from sqlalchemy import select

from apoio import cadastrar, criar_cliente, login, obter_csrf

OFX = """OFXHEADER:100
DATA:OFXSGML
CHARSET:1252

<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS>
<BANKACCTFROM><ACCTID>12345-6</BANKACCTFROM>
<BANKTRANLIST>
<STMTTRN><DTPOSTED>20261110120000[-3:BRT]<TRNAMT>-50.00<FITID>F1<MEMO>Padaria São João</STMTTRN>
<STMTTRN><DTPOSTED>20261105<TRNAMT>1500.00<FITID>F2<NAME>Salário</STMTTRN>
</BANKTRANLIST>
</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""


def _arquivo(texto, codificacao="cp1252"):
    return base64.b64encode(texto.encode(codificacao)).decode()


async def _previa(client, texto=OFX, esperado=200, **extras):
    csrf = await obter_csrf(client)
    resposta = await client.post(
        "/importacoes/previa",
        json={"arquivo_base64": _arquivo(texto), **extras},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == esperado, resposta.text
    return resposta.json()


async def _importar(client, itens, esperado=201):
    csrf = await obter_csrf(client)
    resposta = await client.post("/importacoes", json={"itens": itens}, headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == esperado, resposta.text
    return resposta.json()


def _para_importar(previa):
    campos = ("data_hora", "valor", "tipo", "nome", "id_externo")
    return [{c: item[c] for c in campos} for item in previa["itens"] if not item["duplicada"]]


async def test_previa_le_o_ofx_e_nao_grava_nada(logado):
    previa = await _previa(logado)

    assert previa["formato"] == "ofx"
    assert previa["total"] == 2
    assert previa["duplicadas"] == 0
    padaria, salario = previa["itens"]
    assert padaria["tipo"] == "despesa"
    assert Decimal(padaria["valor"]) == Decimal("50.00")
    assert padaria["nome"] == "Padaria São João"
    assert padaria["data_hora"] == "2026-11-10T12:00:00-03:00"
    assert salario["tipo"] == "receita"
    assert salario["data_hora"] == "2026-11-05T12:00:00-03:00"
    assert (await logado.get("/transacoes")).json() == []


async def test_importar_cria_as_transacoes(logado):
    resultado = await _importar(logado, _para_importar(await _previa(logado)))

    assert resultado == {"criadas": 2, "ignoradas": 0}
    transacoes = (await logado.get("/transacoes")).json()
    assert {t["nome"] for t in transacoes} == {"Padaria São João", "Salário"}
    assert {t["id_externo"] for t in transacoes} == {"ofx:12345-6:F1", "ofx:12345-6:F2"}


async def test_reimportar_o_mesmo_arquivo_nao_duplica(logado):
    itens = _para_importar(await _previa(logado))
    await _importar(logado, itens)

    nova_previa = await _previa(logado)
    assert nova_previa["duplicadas"] == 2
    assert all(item["duplicada"] for item in nova_previa["itens"])

    assert await _importar(logado, itens) == {"criadas": 0, "ignoradas": 2}
    assert len((await logado.get("/transacoes")).json()) == 2


async def test_item_repetido_na_mesma_importacao_entra_uma_vez(logado):
    item = _para_importar(await _previa(logado))[0]

    assert await _importar(logado, [item, item]) == {"criadas": 1, "ignoradas": 1}


async def test_cada_usuario_tem_suas_proprias_importacoes(logado):
    await _importar(logado, _para_importar(await _previa(logado)))

    async with criar_cliente() as bia:
        await cadastrar(bia, email="bia@example.com", nome="Bia")
        await login(bia, email="bia@example.com")
        previa = await _previa(bia)
        assert previa["duplicadas"] == 0
        assert await _importar(bia, _para_importar(previa)) == {"criadas": 2, "ignoradas": 0}


async def test_importar_aceita_ajustes_feitos_na_previa(logado, db):
    from models.categoria import Categoria

    padrao = await db.scalar(select(Categoria.id_categoria).where(Categoria.id_usuario.is_(None)).limit(1))
    item = _para_importar(await _previa(logado))[0]
    item.update(nome="Pão", id_categoria=str(padrao), forma_pagamento="pix", descricao="Café da manhã")

    await _importar(logado, [item])

    (transacao,) = (await logado.get("/transacoes")).json()
    assert transacao["nome"] == "Pão"
    assert transacao["id_categoria"] == str(padrao)
    assert transacao["forma_pagamento"] == "pix"


async def test_importar_recusa_categoria_alheia(logado):
    async with criar_cliente() as bia:
        await cadastrar(bia, email="bia@example.com", nome="Bia")
        await login(bia, email="bia@example.com")
        csrf = await obter_csrf(bia)
        alheia = (
            await bia.post("/categorias", json={"nome": "Da Bia"}, headers={"X-CSRF-Token": csrf})
        ).json()["id_categoria"]

    item = _para_importar(await _previa(logado))[0]
    item["id_categoria"] = alheia

    await _importar(logado, [item], esperado=422)
    assert (await logado.get("/transacoes")).json() == []


@pytest.mark.parametrize(
    "ajuste",
    [{"valor": "0"}, {"valor": "-5"}, {"id_externo": ""}, {"tipo": "outro"}, {"data_hora": "2026-11-10T12:00:00"}],
)
async def test_importar_valida_cada_item(logado, ajuste):
    item = _para_importar(await _previa(logado))[0]
    item.update(ajuste)

    await _importar(logado, [item], esperado=422)


async def test_fatura_de_cartao_com_sinal_invertido(logado):
    texto = "date,title,amount\n2026-11-10,Livraria,89.90\n2026-11-11,Estorno,-20.00\n"

    previa = await _previa(logado, texto, inverter_sinal=True)

    livraria, estorno = previa["itens"]
    assert previa["formato"] == "csv"
    assert (livraria["tipo"], Decimal(livraria["valor"])) == ("despesa", Decimal("89.90"))
    assert (estorno["tipo"], Decimal(estorno["valor"])) == ("receita", Decimal("20.00"))


async def test_data_sem_fuso_usa_o_fuso_do_usuario(logado):
    csrf = await obter_csrf(logado)
    await logado.patch("/auth/me", json={"fuso": "Asia/Tokyo"}, headers={"X-CSRF-Token": csrf})

    previa = await _previa(logado)

    assert previa["itens"][1]["data_hora"] == "2026-11-05T12:00:00+09:00"


async def test_colunas_desconhecidas_pedem_mapeamento(logado):
    texto = "Quando;Quanto;O quê\n10/11/2026;-30,00;Mercado\n"

    erro = await _previa(logado, texto, esperado=422)
    assert erro["detail"]["colunas"] == ["Quando", "Quanto", "O quê"]

    previa = await _previa(
        logado, texto, mapeamento={"data": "Quando", "valor": "Quanto", "descricao": "O quê"}
    )
    assert previa["itens"][0]["nome"] == "Mercado"


async def test_aceita_data_url_do_navegador(logado):
    csrf = await obter_csrf(logado)
    resposta = await logado.post(
        "/importacoes/previa",
        json={"arquivo_base64": "data:application/x-ofx;base64," + _arquivo(OFX)},
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200


@pytest.mark.parametrize("arquivo", ["isto não é base64!", "QUJD$$"])
async def test_base64_invalido(logado, arquivo):
    csrf = await obter_csrf(logado)
    resposta = await logado.post(
        "/importacoes/previa", json={"arquivo_base64": arquivo}, headers={"X-CSRF-Token": csrf}
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"]["mensagem"] == "Arquivo inválido."


async def test_arquivo_grande_demais(logado):
    from schemas.importacao import TAMANHO_MAXIMO_ARQUIVO

    grande = base64.b64encode(b"a" * (TAMANHO_MAXIMO_ARQUIVO + 1)).decode()
    csrf = await obter_csrf(logado)
    resposta = await logado.post(
        "/importacoes/previa", json={"arquivo_base64": grande}, headers={"X-CSRF-Token": csrf}
    )

    assert resposta.status_code == 422


async def test_arquivo_sem_lancamentos(logado):
    erro = await _previa(logado, "Data;Descrição;Valor\n", esperado=422)
    assert erro["detail"]["mensagem"] == "Nenhum lançamento encontrado no arquivo."


async def test_exige_csrf_e_login(logado):
    resposta = await logado.post("/importacoes/previa", json={"arquivo_base64": _arquivo(OFX)})
    assert resposta.status_code == 403

    async with criar_cliente() as anonimo:
        resposta = await anonimo.post("/importacoes", json={"itens": []})
        assert resposta.status_code in (401, 403)
