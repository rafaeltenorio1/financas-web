"""Especificação do CRUD de transações (/transacoes).

Contrato:
- Todas as rotas exigem login. Rotas que alteram dados exigem Origin e X-CSRF-Token.
- id_usuario vem sempre da sessão e não aparece na resposta.
- Transação inexistente ou de outro usuário: 404 (nunca 403).
- id_categoria precisa ser categoria padrão ou do próprio usuário; senão, 422.
- Listagem: filtros data_inicio (inclusive) e data_fim (exclusive), tipo, id_categoria;
  limit (padrão 50, máximo 100) e offset; ordem por data_hora decrescente.
- PATCH altera só os campos enviados; campos obrigatórios não aceitam null.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from apoio import cadastrar, criar_cliente, login, obter_csrf

DATA = "2026-11-05T12:00:00-03:00"


def _dados(**extra):
    return {"valor": "150.75", "data_hora": DATA, "tipo": "despesa", **extra}


async def _criar(client, csrf, **extra):
    resposta = await client.post(
        "/transacoes", json=_dados(**extra), headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


@pytest.fixture
async def csrf(logado):
    return await obter_csrf(logado)


@pytest.fixture
async def outro_usuario():
    """Segundo usuário logado num navegador separado, para os testes de IDOR."""
    async with criar_cliente() as c:
        await cadastrar(c, email="bia@example.com", nome="Bia")
        await login(c, email="bia@example.com")
        yield c


async def _categoria_padrao(db):
    from models.categoria import Categoria

    return await db.scalar(select(Categoria).where(Categoria.id_usuario.is_(None)).limit(1))


async def _categoria_de(db, email, nome="Categoria própria"):
    from models.categoria import Categoria
    from models.usuario import Usuario

    usuario = await db.scalar(select(Usuario).where(Usuario.email == email))
    categoria = Categoria(id_usuario=usuario.id_usuario, nome=nome)
    db.add(categoria)
    await db.commit()
    return categoria


# --- Criar -----------------------------------------------------------------


async def test_cria_transacao(logado, csrf):
    criada = await _criar(logado, csrf, nome="Mercado", forma_pagamento="pix")

    assert criada["nome"] == "Mercado"
    assert Decimal(criada["valor"]) == Decimal("150.75")
    assert criada["tipo"] == "despesa"
    assert criada["forma_pagamento"] == "pix"
    assert criada["id_conta_recorrente"] is None
    assert criada["id_categoria"] is None
    assert "id_transacao" in criada
    # O dono é implícito: não precisa (nem deve) aparecer na resposta.
    assert "id_usuario" not in criada


async def test_criar_ignora_id_usuario_enviado_no_corpo(logado, csrf, outro_usuario, db):
    from models.transacao import Transacao
    from models.usuario import Usuario

    bia = await db.scalar(select(Usuario).where(Usuario.email == "bia@example.com"))
    criada = await _criar(logado, csrf, id_usuario=str(bia.id_usuario))

    transacao = await db.get(Transacao, criada["id_transacao"])
    assert transacao.id_usuario != bia.id_usuario


async def test_cria_com_categoria_padrao(logado, csrf, db):
    categoria = await _categoria_padrao(db)
    criada = await _criar(logado, csrf, id_categoria=str(categoria.id_categoria))
    assert criada["id_categoria"] == str(categoria.id_categoria)


async def test_cria_com_categoria_propria(logado, csrf, db):
    categoria = await _categoria_de(db, "ana@example.com")
    criada = await _criar(logado, csrf, id_categoria=str(categoria.id_categoria))
    assert criada["id_categoria"] == str(categoria.id_categoria)


async def test_nao_aceita_categoria_de_outro_usuario(logado, csrf, outro_usuario, db):
    categoria_da_bia = await _categoria_de(db, "bia@example.com")

    resposta = await logado.post(
        "/transacoes",
        json=_dados(id_categoria=str(categoria_da_bia.id_categoria)),
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 422


async def test_nao_aceita_categoria_inexistente(logado, csrf):
    resposta = await logado.post(
        "/transacoes",
        json=_dados(id_categoria="00000000-0000-0000-0000-000000000000"),
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 422


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("valor", "0"),
        ("valor", "-10"),
        ("valor", "10.123"),
        ("valor", "12345678901.00"),
        ("data_hora", "2026-11-05T12:00:00"),  # sem fuso horário
        ("tipo", "transferencia"),
        ("forma_pagamento", "cheque"),
        ("nome", "x" * 256),
        ("descricao", "x" * 1001),
    ],
)
async def test_rejeita_dados_invalidos(logado, csrf, campo, valor):
    resposta = await logado.post(
        "/transacoes", json=_dados(**{campo: valor}), headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 422


async def test_criar_exige_csrf(logado):
    resposta = await logado.post("/transacoes", json=_dados())
    assert resposta.status_code == 403


async def test_criar_exige_login(client):
    resposta = await client.post(
        "/transacoes", json=_dados(), headers={"X-CSRF-Token": "qualquer"}
    )
    assert resposta.status_code in (401, 403)


# --- Ler -------------------------------------------------------------------


async def test_busca_transacao_por_id(logado, csrf):
    criada = await _criar(logado, csrf)
    resposta = await logado.get(f"/transacoes/{criada['id_transacao']}")
    assert resposta.status_code == 200
    assert resposta.json() == criada


async def test_busca_inexistente_retorna_404(logado):
    resposta = await logado.get("/transacoes/00000000-0000-0000-0000-000000000000")
    assert resposta.status_code == 404


async def test_listar_exige_login(client):
    assert (await client.get("/transacoes")).status_code == 401


async def test_lista_so_as_proprias_em_ordem_decrescente(logado, csrf, outro_usuario):
    await _criar(logado, csrf, nome="antiga", data_hora="2026-11-01T10:00:00-03:00")
    await _criar(logado, csrf, nome="nova", data_hora="2026-11-10T10:00:00-03:00")
    await _criar(logado, csrf, nome="meio", data_hora="2026-11-05T10:00:00-03:00")

    csrf_bia = await obter_csrf(outro_usuario)
    await _criar(outro_usuario, csrf_bia, nome="da bia")

    resposta = await logado.get("/transacoes")
    assert resposta.status_code == 200
    assert [t["nome"] for t in resposta.json()] == ["nova", "meio", "antiga"]


async def test_filtra_por_periodo(logado, csrf):
    await _criar(logado, csrf, nome="outubro", data_hora="2026-10-31T23:59:59-03:00")
    await _criar(logado, csrf, nome="inicio", data_hora="2026-11-01T00:00:00-03:00")
    await _criar(logado, csrf, nome="fim", data_hora="2026-11-30T23:59:59-03:00")
    await _criar(logado, csrf, nome="dezembro", data_hora="2026-12-01T00:00:00-03:00")

    resposta = await logado.get(
        "/transacoes",
        params={
            "data_inicio": "2026-11-01T00:00:00-03:00",
            "data_fim": "2026-12-01T00:00:00-03:00",
        },
    )
    assert resposta.status_code == 200
    assert [t["nome"] for t in resposta.json()] == ["fim", "inicio"]


async def test_filtra_por_tipo(logado, csrf):
    await _criar(logado, csrf, nome="salario", tipo="receita")
    await _criar(logado, csrf, nome="aluguel", tipo="despesa")

    resposta = await logado.get("/transacoes", params={"tipo": "receita"})
    assert [t["nome"] for t in resposta.json()] == ["salario"]


async def test_filtra_por_categoria(logado, csrf, db):
    categoria = await _categoria_padrao(db)
    await _criar(logado, csrf, nome="com", id_categoria=str(categoria.id_categoria))
    await _criar(logado, csrf, nome="sem")

    resposta = await logado.get(
        "/transacoes", params={"id_categoria": str(categoria.id_categoria)}
    )
    assert [t["nome"] for t in resposta.json()] == ["com"]


async def test_paginacao(logado, csrf):
    for dia in range(1, 6):
        await _criar(logado, csrf, nome=f"dia {dia}", data_hora=f"2026-11-0{dia}T10:00:00-03:00")

    pagina = await logado.get("/transacoes", params={"limit": 2, "offset": 1})
    assert [t["nome"] for t in pagina.json()] == ["dia 4", "dia 3"]


@pytest.mark.parametrize("params", [{"limit": 101}, {"limit": 0}, {"offset": -1}])
async def test_paginacao_rejeita_limites_invalidos(logado, params):
    assert (await logado.get("/transacoes", params=params)).status_code == 422


# --- Editar ----------------------------------------------------------------


async def test_patch_altera_so_os_campos_enviados(logado, csrf):
    criada = await _criar(logado, csrf, nome="Mercado", descricao="compras do mês")

    resposta = await logado.patch(
        f"/transacoes/{criada['id_transacao']}",
        json={"valor": "200.00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 200
    editada = resposta.json()
    assert Decimal(editada["valor"]) == Decimal("200.00")
    assert editada["nome"] == "Mercado"
    assert editada["descricao"] == "compras do mês"
    assert editada["tipo"] == criada["tipo"]


async def test_patch_pode_limpar_campo_opcional(logado, csrf, db):
    categoria = await _categoria_padrao(db)
    criada = await _criar(logado, csrf, id_categoria=str(categoria.id_categoria))

    resposta = await logado.patch(
        f"/transacoes/{criada['id_transacao']}",
        json={"id_categoria": None, "descricao": None},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 200
    assert resposta.json()["id_categoria"] is None


@pytest.mark.parametrize("campo", ["valor", "data_hora", "tipo"])
async def test_patch_nao_aceita_null_em_campo_obrigatorio(logado, csrf, campo):
    criada = await _criar(logado, csrf)
    resposta = await logado.patch(
        f"/transacoes/{criada['id_transacao']}",
        json={campo: None},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 422


async def test_patch_valida_valor(logado, csrf):
    criada = await _criar(logado, csrf)
    resposta = await logado.patch(
        f"/transacoes/{criada['id_transacao']}",
        json={"valor": "-5"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 422


async def test_patch_nao_aceita_categoria_de_outro_usuario(logado, csrf, outro_usuario, db):
    criada = await _criar(logado, csrf)
    categoria_da_bia = await _categoria_de(db, "bia@example.com")

    resposta = await logado.patch(
        f"/transacoes/{criada['id_transacao']}",
        json={"id_categoria": str(categoria_da_bia.id_categoria)},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 422


async def test_patch_exige_csrf(logado, csrf):
    criada = await _criar(logado, csrf)
    resposta = await logado.patch(
        f"/transacoes/{criada['id_transacao']}", json={"valor": "1.00"}
    )
    assert resposta.status_code == 403


# --- Apagar ----------------------------------------------------------------


async def test_apaga_transacao(logado, csrf):
    criada = await _criar(logado, csrf)
    url = f"/transacoes/{criada['id_transacao']}"

    resposta = await logado.delete(url, headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == 204
    assert resposta.content == b""
    assert (await logado.get(url)).status_code == 404


async def test_apagar_inexistente_retorna_404(logado, csrf):
    resposta = await logado.delete(
        "/transacoes/00000000-0000-0000-0000-000000000000",
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 404


async def test_apagar_exige_csrf(logado, csrf):
    criada = await _criar(logado, csrf)
    resposta = await logado.delete(f"/transacoes/{criada['id_transacao']}")
    assert resposta.status_code == 403


# --- IDOR: um usuário nunca alcança a transação de outro -------------------


async def test_outro_usuario_nao_ve_edita_nem_apaga(logado, csrf, outro_usuario):
    criada = await _criar(logado, csrf, nome="só da Ana", valor="99.90")
    url = f"/transacoes/{criada['id_transacao']}"
    csrf_bia = await obter_csrf(outro_usuario)

    assert (await outro_usuario.get(url)).status_code == 404
    assert (
        await outro_usuario.patch(url, json={"valor": "1.00"}, headers={"X-CSRF-Token": csrf_bia})
    ).status_code == 404
    assert (
        await outro_usuario.delete(url, headers={"X-CSRF-Token": csrf_bia})
    ).status_code == 404
    assert (await outro_usuario.get("/transacoes")).json() == []

    # A transação da Ana continua intacta.
    intacta = (await logado.get(url)).json()
    assert intacta == criada


async def test_filtro_por_categoria_nao_vaza_dados_de_outro(logado, csrf, outro_usuario, db):
    categoria = await _categoria_padrao(db)
    await _criar(logado, csrf, id_categoria=str(categoria.id_categoria))

    resposta = await outro_usuario.get(
        "/transacoes", params={"id_categoria": str(categoria.id_categoria)}
    )
    assert resposta.json() == []
