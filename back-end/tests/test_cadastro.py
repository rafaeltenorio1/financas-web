from sqlalchemy import select

from apoio import cadastrar


async def test_cadastro_cria_usuario_sem_expor_senha(client, db):
    from models.usuario import Usuario

    dados = await cadastrar(client, email="ana@example.com")

    assert set(dados) == {"id_usuario", "nome", "email", "dois_fatores", "email_verificado"}
    assert dados["email_verificado"] is False
    usuario = await db.scalar(select(Usuario).where(Usuario.email == "ana@example.com"))
    assert usuario is not None
    # A senha é guardada como hash Argon2, nunca em texto puro.
    assert usuario.senha_hash.startswith("$argon2")
    assert "senha-forte-123" not in usuario.senha_hash


async def test_cadastro_normaliza_email(client):
    dados = await cadastrar(client, email="  Ana@Example.COM ")
    assert dados["email"] == "ana@example.com"


async def test_email_duplicado_retorna_409_generico(client):
    await cadastrar(client, email="ana@example.com")

    resposta = await client.post(
        "/auth/register",
        json={"nome": "Outra", "email": "ANA@example.com", "senha": "outra-senha-123"},
    )

    assert resposta.status_code == 409
    # Mensagem genérica: não confirma que o e-mail já existe.
    assert "e-mail" not in resposta.json()["detail"].lower()


async def test_cadastro_rejeita_email_invalido(client):
    resposta = await client.post(
        "/auth/register", json={"nome": "Ana", "email": "nao-e-email", "senha": "senha-forte-123"}
    )
    assert resposta.status_code == 422


async def test_cadastro_rejeita_senha_curta(client):
    resposta = await client.post(
        "/auth/register", json={"nome": "Ana", "email": "ana@example.com", "senha": "curta"}
    )
    assert resposta.status_code == 422


async def test_cadastro_rejeita_nome_vazio(client):
    resposta = await client.post(
        "/auth/register", json={"nome": "", "email": "ana@example.com", "senha": "senha-forte-123"}
    )
    assert resposta.status_code == 422
