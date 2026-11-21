from sqlalchemy import select


async def test_saude_confere_api_e_banco(client):
    resposta = await client.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"api": "ok", "banco": True}


async def test_categorias_lista_as_padrao_em_ordem(client, db):
    from models.categoria import Categoria

    resposta = await client.get("/categorias")
    assert resposta.status_code == 200

    nomes = [c["nome"] for c in resposta.json()]
    assert nomes, "as migrações deveriam ter criado as categorias padrão"
    # Compara com a ordem do próprio Postgres: a collation trata acentos
    # ("Açougue" antes de "Adicional"), diferente do sorted() do Python.
    padrao = (
        await db.scalars(
            select(Categoria.nome)
            .where(Categoria.id_usuario.is_(None))
            .order_by(Categoria.nome)
        )
    ).all()
    assert nomes == list(padrao)


async def test_categorias_nao_mostra_categoria_de_usuario(logado, db):
    from models.categoria import Categoria
    from models.usuario import Usuario

    usuario = await db.scalar(select(Usuario))
    db.add(Categoria(id_usuario=usuario.id_usuario, nome="Minha categoria secreta"))
    await db.commit()

    nomes = [c["nome"] for c in (await logado.get("/categorias")).json()]
    assert "Minha categoria secreta" not in nomes
