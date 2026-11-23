"""Categorias: padrão (compartilhadas, só leitura) + as do próprio usuário.

Contrato:
- Todas as rotas exigem login; as que alteram dados exigem Origin e X-CSRF-Token.
- Listagem: padrão + do usuário, em ordem de nome; ?tipo= traz o tipo pedido e as sem tipo.
- Nome duplicado (sem diferenciar maiúsculas) entre padrão + do usuário: 409.
- Editar/apagar padrão: 403. De outro usuário ou inexistente: 404.
- Apagar uma categoria deixa as transações dela sem categoria.
- Cor: hex #rrggbb gravado em minúsculas; sem cor no POST, o servidor usa o pastel
  menos usado pela pessoa; padrão já vêm com cor (migração de dados) e não mudam.
- Ícone: opcional, formato c-<nome>; nulo deixa o front escolher. Padrão vêm sem ícone.
  No PATCH, null volta ao automático e omitir mantém o atual.
"""

import pytest
from sqlalchemy import select

from apoio import cadastrar, criar_cliente, login, obter_csrf

INEXISTENTE = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
async def csrf(logado):
    return await obter_csrf(logado)


@pytest.fixture
async def outro_usuario():
    async with criar_cliente() as c:
        await cadastrar(c, email="bia@example.com", nome="Bia")
        await login(c, email="bia@example.com")
        yield c


async def _criar(client, csrf, nome="Pet", tipo_padrao="despesa"):
    resposta = await client.post(
        "/categorias",
        json={"nome": nome, "tipo_padrao": tipo_padrao},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


async def _uma_padrao(db):
    from models.categoria import Categoria

    return await db.scalar(
        select(Categoria).where(Categoria.id_usuario.is_(None)).order_by(Categoria.nome).limit(1)
    )


# --- Listar ----------------------------------------------------------------


async def test_listar_exige_login(client):
    assert (await client.get("/categorias")).status_code == 401


async def test_lista_padrao_em_ordem_do_banco(logado, db):
    from models.categoria import Categoria

    resposta = await logado.get("/categorias")
    assert resposta.status_code == 200
    categorias = resposta.json()

    # Ordem do próprio Postgres: a collation trata acentos ("Açougue" antes de "Adicional").
    padrao = (
        await db.scalars(
            select(Categoria.nome)
            .where(Categoria.id_usuario.is_(None))
            .order_by(Categoria.nome)
        )
    ).all()
    assert padrao, "as migrações deveriam ter criado as categorias padrão"
    assert [c["nome"] for c in categorias] == list(padrao)
    assert all(c["padrao"] is True for c in categorias)
    # O dono não é exposto: o front só precisa saber se é padrão.
    assert all(set(c) == {"id_categoria", "nome", "tipo_padrao", "cor", "icone", "padrao"} for c in categorias)


async def test_lista_inclui_as_proprias_e_nao_as_de_outro(logado, csrf, outro_usuario):
    await _criar(logado, csrf, nome="Pet da Ana")
    await _criar(outro_usuario, await obter_csrf(outro_usuario), nome="Pet da Bia")

    nomes = {c["nome"]: c for c in (await logado.get("/categorias")).json()}
    assert nomes["Pet da Ana"]["padrao"] is False
    assert "Pet da Bia" not in nomes


async def test_filtro_por_tipo_inclui_as_sem_tipo(logado, csrf):
    await _criar(logado, csrf, nome="Só despesa", tipo_padrao="despesa")
    await _criar(logado, csrf, nome="Só receita", tipo_padrao="receita")
    await _criar(logado, csrf, nome="Qualquer tipo", tipo_padrao=None)

    resposta = await logado.get("/categorias", params={"tipo": "despesa"})
    categorias = resposta.json()
    nomes = {c["nome"] for c in categorias}

    assert {"Só despesa", "Qualquer tipo"} <= nomes
    assert "Só receita" not in nomes
    assert all(c["tipo_padrao"] in ("despesa", None) for c in categorias)


async def test_filtro_por_tipo_invalido(logado):
    assert (await logado.get("/categorias", params={"tipo": "outro"})).status_code == 422


# --- Criar -----------------------------------------------------------------


async def test_cria_categoria_propria(logado, csrf, db):
    from models.categoria import Categoria
    from models.usuario import Usuario

    criada = await _criar(logado, csrf, nome="  Pet  ", tipo_padrao="despesa")

    assert criada["nome"] == "Pet"  # espaços nas pontas removidos
    assert criada["tipo_padrao"] == "despesa"
    assert criada["padrao"] is False

    categoria = await db.get(Categoria, criada["id_categoria"])
    ana = await db.scalar(select(Usuario).where(Usuario.email == "ana@example.com"))
    assert categoria.id_usuario == ana.id_usuario


async def test_cria_sem_tipo(logado, csrf):
    criada = await _criar(logado, csrf, nome="Diversos", tipo_padrao=None)
    assert criada["tipo_padrao"] is None


async def test_nome_igual_a_padrao_e_recusado(logado, csrf, db):
    padrao = await _uma_padrao(db)

    resposta = await logado.post(
        "/categorias",
        json={"nome": padrao.nome.upper()},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 409


async def test_nome_repetido_entre_as_proprias_e_recusado(logado, csrf):
    await _criar(logado, csrf, nome="Pet")

    resposta = await logado.post(
        "/categorias", json={"nome": "pET"}, headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 409


async def test_mesmo_nome_em_usuarios_diferentes_e_permitido(logado, csrf, outro_usuario):
    await _criar(logado, csrf, nome="Pet")
    await _criar(outro_usuario, await obter_csrf(outro_usuario), nome="Pet")


@pytest.mark.parametrize(
    "corpo",
    [
        {"nome": ""},
        {"nome": "   "},
        {"nome": "x" * 101},
        {"nome": "Pet", "tipo_padrao": "outro"},
        {},
    ],
)
async def test_criar_rejeita_dados_invalidos(logado, csrf, corpo):
    resposta = await logado.post("/categorias", json=corpo, headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == 422


async def test_criar_exige_csrf(logado):
    resposta = await logado.post("/categorias", json={"nome": "Pet"})
    assert resposta.status_code == 403


async def test_criar_exige_login(client):
    resposta = await client.post(
        "/categorias", json={"nome": "Pet"}, headers={"X-CSRF-Token": "qualquer"}
    )
    assert resposta.status_code in (401, 403)


# --- Editar ----------------------------------------------------------------


async def test_edita_nome_e_tipo(logado, csrf):
    criada = await _criar(logado, csrf, nome="Pet", tipo_padrao="despesa")

    resposta = await logado.patch(
        f"/categorias/{criada['id_categoria']}",
        json={"nome": "Animais", "tipo_padrao": None},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Animais"
    assert resposta.json()["tipo_padrao"] is None


async def test_patch_altera_so_o_enviado(logado, csrf):
    criada = await _criar(logado, csrf, nome="Pet", tipo_padrao="despesa")

    resposta = await logado.patch(
        f"/categorias/{criada['id_categoria']}",
        json={"nome": "Animais"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.json()["tipo_padrao"] == "despesa"


async def test_patch_pode_mudar_so_maiusculas_do_proprio_nome(logado, csrf):
    criada = await _criar(logado, csrf, nome="pet")

    resposta = await logado.patch(
        f"/categorias/{criada['id_categoria']}",
        json={"nome": "Pet"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Pet"


async def test_patch_nome_null_e_recusado(logado, csrf):
    criada = await _criar(logado, csrf)
    resposta = await logado.patch(
        f"/categorias/{criada['id_categoria']}",
        json={"nome": None},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 422


async def test_patch_para_nome_em_uso_e_recusado(logado, csrf, db):
    padrao = await _uma_padrao(db)
    await _criar(logado, csrf, nome="Outra")
    criada = await _criar(logado, csrf, nome="Pet")
    url = f"/categorias/{criada['id_categoria']}"

    for nome in ("outra", padrao.nome):
        resposta = await logado.patch(url, json={"nome": nome}, headers={"X-CSRF-Token": csrf})
        assert resposta.status_code == 409


async def test_editar_padrao_e_proibido(logado, csrf, db):
    padrao = await _uma_padrao(db)
    nome_original = padrao.nome

    resposta = await logado.patch(
        f"/categorias/{padrao.id_categoria}",
        json={"nome": "Hackeada"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 403

    await db.refresh(padrao)
    assert padrao.nome == nome_original


async def test_editar_inexistente_retorna_404(logado, csrf):
    resposta = await logado.patch(
        f"/categorias/{INEXISTENTE}", json={"nome": "X"}, headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 404


async def test_editar_exige_csrf(logado, csrf):
    criada = await _criar(logado, csrf)
    resposta = await logado.patch(f"/categorias/{criada['id_categoria']}", json={"nome": "X"})
    assert resposta.status_code == 403


# --- Apagar ----------------------------------------------------------------


async def test_apaga_e_transacoes_ficam_sem_categoria(logado, csrf):
    criada = await _criar(logado, csrf)
    transacao = (
        await logado.post(
            "/transacoes",
            json={
                "valor": "30.00",
                "data_hora": "2026-11-05T12:00:00-03:00",
                "tipo": "despesa",
                "id_categoria": criada["id_categoria"],
            },
            headers={"X-CSRF-Token": csrf},
        )
    ).json()

    resposta = await logado.delete(
        f"/categorias/{criada['id_categoria']}", headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 204
    assert resposta.content == b""

    nomes = [c["nome"] for c in (await logado.get("/categorias")).json()]
    assert "Pet" not in nomes

    depois = (await logado.get(f"/transacoes/{transacao['id_transacao']}")).json()
    assert depois["id_categoria"] is None


async def test_apagar_padrao_e_proibido(logado, csrf, db):
    padrao = await _uma_padrao(db)
    resposta = await logado.delete(
        f"/categorias/{padrao.id_categoria}", headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 403


async def test_apagar_inexistente_retorna_404(logado, csrf):
    resposta = await logado.delete(f"/categorias/{INEXISTENTE}", headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == 404


async def test_apagar_exige_csrf(logado, csrf):
    criada = await _criar(logado, csrf)
    resposta = await logado.delete(f"/categorias/{criada['id_categoria']}")
    assert resposta.status_code == 403


# --- IDOR ------------------------------------------------------------------


async def test_outro_usuario_nao_edita_nem_apaga(logado, csrf, outro_usuario):
    criada = await _criar(logado, csrf, nome="Pet da Ana")
    url = f"/categorias/{criada['id_categoria']}"
    csrf_bia = await obter_csrf(outro_usuario)

    assert (
        await outro_usuario.patch(url, json={"nome": "Roubada"}, headers={"X-CSRF-Token": csrf_bia})
    ).status_code == 404
    assert (await outro_usuario.delete(url, headers={"X-CSRF-Token": csrf_bia})).status_code == 404

    nomes = [c["nome"] for c in (await logado.get("/categorias")).json()]
    assert "Pet da Ana" in nomes


# --- Cor -------------------------------------------------------------------

PASTEIS = ["#7dbde8", "#f0a27a", "#a996ee", "#62c4b8", "#ddc170", "#ec93b8"]


async def test_padrao_vem_com_cor_por_tema(logado):
    categorias = {c["nome"]: c["cor"] for c in (await logado.get("/categorias")).json()}
    assert all(cor in PASTEIS for cor in categorias.values())
    assert categorias["Aluguel"] == categorias["Condomínio"] == "#7dbde8"
    assert categorias["Supermercado/Feira"] == "#f0a27a"
    assert categorias["Combustível"] == "#ddc170"


async def test_cria_com_cor_escolhida_em_minusculas(logado, csrf):
    resposta = await logado.post(
        "/categorias", json={"nome": "Pet", "cor": " #12AB9F "}, headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["cor"] == "#12ab9f"


async def test_sem_cor_usa_o_pastel_menos_usado(logado, csrf):
    cores = [(await _criar(logado, csrf, nome=f"Minha {i}"))["cor"] for i in range(7)]
    assert cores[:6] == PASTEIS
    assert cores[6] == PASTEIS[0]


async def test_cor_automatica_ignora_cores_personalizadas_e_outros_usuarios(logado, csrf, outro_usuario):
    await logado.post("/categorias", json={"nome": "Livre", "cor": "#000000"}, headers={"X-CSRF-Token": csrf})
    csrf_bia = await obter_csrf(outro_usuario)
    for nome in ("Da Bia 1", "Da Bia 2"):
        await _criar(outro_usuario, csrf_bia, nome=nome)
    assert (await _criar(logado, csrf, nome="Primeira pastel"))["cor"] == PASTEIS[0]


@pytest.mark.parametrize("cor", ["7dbde8", "#7dbde", "#7dbde8f", "#gggggg", "red", "#7dbde8;}", ""])
async def test_cor_invalida_retorna_422(logado, csrf, cor):
    resposta = await logado.post(
        "/categorias", json={"nome": "Pet", "cor": cor}, headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 422


async def test_edita_a_cor(logado, csrf):
    criada = await _criar(logado, csrf)
    resposta = await logado.patch(
        f"/categorias/{criada['id_categoria']}", json={"cor": "#ABCDEF"}, headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["cor"] == "#abcdef"
    assert resposta.json()["nome"] == criada["nome"]


async def test_editar_cor_nula_retorna_422(logado, csrf):
    criada = await _criar(logado, csrf)
    resposta = await logado.patch(
        f"/categorias/{criada['id_categoria']}", json={"cor": None}, headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 422


async def test_cor_da_padrao_nao_muda(logado, csrf, db):
    padrao = await _uma_padrao(db)
    resposta = await logado.patch(
        f"/categorias/{padrao.id_categoria}", json={"cor": "#000000"}, headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 403


async def test_banco_recusa_cor_fora_do_formato(db):
    from sqlalchemy.exc import IntegrityError

    from models.categoria import Categoria

    db.add(Categoria(nome="Direto no banco", cor="#ABCDEF"))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()



# --- Ícone -----------------------------------------------------------------


async def test_padrao_vem_sem_icone(logado):
    categorias = (await logado.get("/categorias")).json()
    assert categorias
    assert all(c["icone"] is None for c in categorias)


async def test_cria_sem_icone_fica_nulo(logado, csrf):
    assert (await _criar(logado, csrf))["icone"] is None


async def test_cria_com_icone(logado, csrf):
    resposta = await logado.post(
        "/categorias", json={"nome": "Pet", "icone": " c-pata-de-gato "}, headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["icone"] == "c-pata-de-gato"


@pytest.mark.parametrize(
    "icone",
    ["pata", "c-", "C-pata", "c-Pata", "c-pata_gato", "c-pata gato", "c-" + "a" * 39, "c-pata\"><svg", ""],
)
async def test_icone_invalido_retorna_422(logado, csrf, icone):
    resposta = await logado.post(
        "/categorias", json={"nome": "Pet", "icone": icone}, headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 422


async def test_icone_no_limite_de_tamanho(logado, csrf):
    icone = "c-" + "a" * 38
    resposta = await logado.post(
        "/categorias", json={"nome": "Pet", "icone": icone}, headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["icone"] == icone


async def test_edita_o_icone_e_omitir_mantem(logado, csrf):
    criada = await _criar(logado, csrf)
    url = f"/categorias/{criada['id_categoria']}"
    resposta = await logado.patch(url, json={"icone": "c-casa"}, headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["icone"] == "c-casa"

    resposta = await logado.patch(url, json={"nome": "Bichos"}, headers={"X-CSRF-Token": csrf})
    assert resposta.json()["icone"] == "c-casa"


async def test_icone_null_volta_ao_automatico(logado, csrf):
    criada = await _criar(logado, csrf)
    url = f"/categorias/{criada['id_categoria']}"
    await logado.patch(url, json={"icone": "c-casa"}, headers={"X-CSRF-Token": csrf})
    resposta = await logado.patch(url, json={"icone": None}, headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["icone"] is None


async def test_icone_da_padrao_nao_muda(logado, csrf, db):
    padrao = await _uma_padrao(db)
    resposta = await logado.patch(
        f"/categorias/{padrao.id_categoria}", json={"icone": "c-casa"}, headers={"X-CSRF-Token": csrf}
    )
    assert resposta.status_code == 403


async def test_banco_recusa_icone_fora_do_formato(db):
    from sqlalchemy.exc import IntegrityError

    from models.categoria import Categoria

    db.add(Categoria(nome="Direto no banco", icone="C-Casa"))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()
