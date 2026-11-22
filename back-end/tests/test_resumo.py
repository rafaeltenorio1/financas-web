from decimal import Decimal

import pytest
from sqlalchemy import select

from apoio import cadastrar, criar_cliente, login, obter_csrf


@pytest.fixture
async def csrf(logado):
    return await obter_csrf(logado)


async def _criar(client, csrf, valor, tipo, data_hora="2026-11-05T12:00:00-03:00", **extra):
    resposta = await client.post(
        "/transacoes",
        json={"valor": valor, "tipo": tipo, "data_hora": data_hora, **extra},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


async def _categoria(db, nome):
    from models.categoria import Categoria

    return await db.scalar(
        select(Categoria).where(Categoria.id_usuario.is_(None), Categoria.nome == nome)
    )


def _dec(resumo, *chaves):
    return [Decimal(resumo[c]) for c in chaves]


async def test_resumo_exige_login(client):
    assert (await client.get("/transacoes/resumo")).status_code == 401


async def test_resumo_vazio(logado):
    resposta = await logado.get("/transacoes/resumo")
    assert resposta.status_code == 200
    resumo = resposta.json()
    assert _dec(resumo, "receitas", "despesas", "saldo") == [0, 0, 0]
    assert resumo["por_categoria"] == []
    assert resumo["por_mes"] == []


async def test_totais_e_saldo(logado, csrf):
    await _criar(logado, csrf, "3200.00", "receita")
    await _criar(logado, csrf, "450.50", "receita")
    await _criar(logado, csrf, "950.00", "despesa")
    await _criar(logado, csrf, "312.40", "despesa")

    resumo = (await logado.get("/transacoes/resumo")).json()

    assert resumo["receitas"] == "3650.50"
    assert resumo["despesas"] == "1262.40"
    assert resumo["saldo"] == "2388.10"


async def test_saldo_pode_ser_negativo(logado, csrf):
    await _criar(logado, csrf, "100.00", "receita")
    await _criar(logado, csrf, "250.00", "despesa")

    resumo = (await logado.get("/transacoes/resumo")).json()
    assert Decimal(resumo["saldo"]) == Decimal("-150.00")


async def test_filtra_por_periodo(logado, csrf):
    await _criar(logado, csrf, "10.00", "despesa", "2026-10-31T23:59:59-03:00")
    await _criar(logado, csrf, "20.00", "despesa", "2026-11-01T00:00:00-03:00")
    await _criar(logado, csrf, "30.00", "despesa", "2026-11-30T23:59:59-03:00")
    await _criar(logado, csrf, "40.00", "despesa", "2026-12-01T00:00:00-03:00")

    resumo = (
        await logado.get(
            "/transacoes/resumo",
            params={
                "data_inicio": "2026-11-01T00:00:00-03:00",
                "data_fim": "2026-12-01T00:00:00-03:00",
            },
        )
    ).json()

    assert Decimal(resumo["despesas"]) == Decimal("50.00")
    assert [m["mes"] for m in resumo["por_mes"]] == ["2026-11"]


async def test_agrupa_por_categoria_e_tipo(logado, csrf, db):
    mercado = await _categoria(db, "Supermercado")
    if mercado is None:
        from models.categoria import Categoria

        mercado = await db.scalar(
            select(Categoria).where(Categoria.id_usuario.is_(None)).order_by(Categoria.nome).limit(1)
        )
    id_mercado = str(mercado.id_categoria)

    await _criar(logado, csrf, "100.00", "despesa", id_categoria=id_mercado)
    await _criar(logado, csrf, "50.00", "despesa", id_categoria=id_mercado)
    await _criar(logado, csrf, "20.00", "receita", id_categoria=id_mercado)
    await _criar(logado, csrf, "500.00", "despesa")

    grupos = (await logado.get("/transacoes/resumo")).json()["por_categoria"]

    assert grupos[0] == {
        "id_categoria": None,
        "nome": None,
        "tipo": "despesa",
        "total": "500.00",
        "quantidade": 1,
    }
    assert grupos[1] == {
        "id_categoria": id_mercado,
        "nome": mercado.nome,
        "tipo": "despesa",
        "total": "150.00",
        "quantidade": 2,
    }
    assert grupos[2] == {
        "id_categoria": id_mercado,
        "nome": mercado.nome,
        "tipo": "receita",
        "total": "20.00",
        "quantidade": 1,
    }
    assert len(grupos) == 3


async def test_agrupa_por_mes_em_ordem(logado, csrf):
    await _criar(logado, csrf, "1000.00", "receita", "2026-12-10T10:00:00-03:00")
    await _criar(logado, csrf, "300.00", "despesa", "2026-10-10T10:00:00-03:00")
    await _criar(logado, csrf, "200.00", "despesa", "2026-12-15T10:00:00-03:00")

    meses = (await logado.get("/transacoes/resumo")).json()["por_mes"]

    assert meses == [
        {"mes": "2026-10", "receitas": "0.00", "despesas": "300.00", "saldo": "-300.00"},
        {"mes": "2026-12", "receitas": "1000.00", "despesas": "200.00", "saldo": "800.00"},
    ]


async def test_mes_respeita_fuso_padrao_de_sao_paulo(logado, csrf):
    await _criar(logado, csrf, "80.00", "despesa", "2026-11-30T22:00:00-03:00")

    meses = (await logado.get("/transacoes/resumo")).json()["por_mes"]
    assert [m["mes"] for m in meses] == ["2026-11"]


async def test_mes_usa_o_fuso_enviado(logado, csrf):
    await _criar(logado, csrf, "80.00", "despesa", "2026-11-30T22:00:00-03:00")

    utc = (await logado.get("/transacoes/resumo", params={"fuso": "UTC"})).json()
    toquio = (await logado.get("/transacoes/resumo", params={"fuso": "Asia/Tokyo"})).json()

    assert [m["mes"] for m in utc["por_mes"]] == ["2026-12"]
    assert [m["mes"] for m in toquio["por_mes"]] == ["2026-12"]


@pytest.mark.parametrize(
    "fuso",
    ["Marte/Olympus", "", "America/Sao_Paulo'; DROP TABLE transacao; --", "x" * 65],
)
async def test_fuso_invalido_e_recusado(logado, csrf, fuso):
    await _criar(logado, csrf, "10.00", "despesa")

    resposta = await logado.get("/transacoes/resumo", params={"fuso": fuso})
    assert resposta.status_code == 422

    assert len((await logado.get("/transacoes")).json()) == 1


async def test_resumo_so_considera_o_proprio_usuario(logado, csrf):
    await _criar(logado, csrf, "100.00", "receita")

    async with criar_cliente() as bia:
        await cadastrar(bia, email="bia@example.com", nome="Bia")
        await login(bia, email="bia@example.com")
        await _criar(bia, await obter_csrf(bia), "9999.00", "receita")

        resumo_bia = (await bia.get("/transacoes/resumo")).json()

    resumo_ana = (await logado.get("/transacoes/resumo")).json()

    assert resumo_ana["receitas"] == "100.00"
    assert resumo_bia["receitas"] == "9999.00"
    assert len(resumo_ana["por_categoria"]) == 1
    assert len(resumo_ana["por_mes"]) == 1


async def test_rota_resumo_nao_conflita_com_busca_por_id(logado, csrf):
    criada = await _criar(logado, csrf, "10.00", "despesa")
    assert (await logado.get(f"/transacoes/{criada['id_transacao']}")).status_code == 200
    assert (await logado.get("/transacoes/resumo")).status_code == 200
