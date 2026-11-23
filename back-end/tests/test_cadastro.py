"""Cadastro sem revelar se o e-mail já tem conta.

Contrato:
- Sempre 202 com a mesma mensagem, sem dados do usuário, para e-mail novo ou existente.
- E-mail novo: cria a conta e envia a verificação.
- E-mail existente (confirmado ou não): não altera a conta e avisa o dono por e-mail,
  no máximo um aviso a cada TOKEN_INTERVALO_ENVIO_MIN (reserva atômica em aviso_cadastro_em).
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from apoio import SENHA_PADRAO, cadastrar, corpo_texto, criar_cliente, login, marcar_verificado

MENSAGEM = "Enviamos um e-mail para você confirmar o cadastro. Confira sua caixa de entrada."


async def _registrar(client, email="ana@example.com", senha=SENHA_PADRAO, nome="Ana"):
    return await client.post("/auth/register", json={"nome": nome, "email": email, "senha": senha})


async def test_cadastro_cria_usuario_sem_expor_dados(client, db, caixa):
    from models.usuario import Usuario

    resposta = await _registrar(client)

    assert resposta.status_code == 202
    assert resposta.json() == {"mensagem": MENSAGEM}
    usuario = await db.scalar(select(Usuario).where(Usuario.email == "ana@example.com"))
    assert usuario is not None
    assert usuario.email_verificado is False
    # A senha é guardada como hash Argon2, nunca em texto puro.
    assert usuario.senha_hash.startswith("$argon2")
    assert SENHA_PADRAO not in usuario.senha_hash
    assert await caixa.assuntos() == ["Confirme seu e-mail"]


async def test_cadastro_nao_abre_sessao(client):
    await cadastrar(client)

    assert "sessao" not in client.cookies
    assert (await client.get("/auth/me")).status_code == 401


async def test_cadastro_normaliza_email(client, db):
    from models.usuario import Usuario

    await cadastrar(client, email="  Ana@Example.COM ")

    assert await db.scalar(select(Usuario.email).where(Usuario.email == "ana@example.com")) is not None


async def test_email_existente_recebe_a_mesma_resposta(client):
    novo = await _registrar(client)
    repetido = await _registrar(client, email="ANA@example.com", nome="Outra", senha="outra-senha-123")

    assert novo.status_code == repetido.status_code == 202
    assert novo.json() == repetido.json()
    assert set(novo.headers) - {"content-length"} == set(repetido.headers) - {"content-length"}


async def test_email_existente_nao_altera_a_conta(client, db):
    from models.usuario import Usuario

    await cadastrar(client)
    antes = await db.scalar(select(Usuario.senha_hash).where(Usuario.email == "ana@example.com"))

    await _registrar(client, nome="Invasor", senha="senha-do-invasor-1")

    db.expire_all()
    usuario = await db.scalar(select(Usuario).where(Usuario.email == "ana@example.com"))
    assert usuario.nome == "Ana"
    assert usuario.senha_hash == antes
    assert (await login(client, senha="senha-do-invasor-1")).status_code == 401
    assert (await login(client)).status_code == 200


async def test_email_existente_avisa_o_dono(client, caixa):
    await cadastrar(client)
    await marcar_verificado()
    await caixa.esvaziar()

    await _registrar(client, nome="Outra pessoa", senha="outra-senha-123")

    mensagens = await caixa.recebidos()
    assert [m["Subject"] for m in mensagens] == ["Tentativa de cadastro com seu e-mail"]
    assert mensagens[0]["To"] == "ana@example.com"
    texto = corpo_texto(mensagens[0])
    assert "Olá, Ana." in texto
    assert "Outra pessoa" not in texto
    assert "/#/entrar" in texto and "/#/esqueci-senha" in texto


async def test_email_existente_nao_confirmado_tambem_e_avisado(client, caixa):
    await cadastrar(client)
    await caixa.esvaziar()

    await _registrar(client)

    assert await caixa.assuntos() == ["Tentativa de cadastro com seu e-mail"]


async def test_aviso_respeita_o_intervalo(client, db, caixa):
    from models.usuario import Usuario

    await cadastrar(client)
    await caixa.esvaziar()

    for _ in range(3):
        assert (await _registrar(client)).status_code == 202
    assert await caixa.assuntos() == ["Tentativa de cadastro com seu e-mail"]

    await caixa.esvaziar()
    passado = datetime.now(timezone.utc) - timedelta(days=1)
    await db.execute(update(Usuario).where(Usuario.email == "ana@example.com").values(aviso_cadastro_em=passado))
    await db.commit()

    await _registrar(client)
    assert await caixa.assuntos() == ["Tentativa de cadastro com seu e-mail"]


async def test_cadastros_simultaneos_do_mesmo_email(db, caixa):
    from models.usuario import Usuario

    async def tentar(nome):
        async with criar_cliente() as c:
            return await _registrar(c, nome=nome)

    respostas = await asyncio.gather(*(tentar(f"Pessoa {i}") for i in range(4)))

    assert {r.status_code for r in respostas} == {202}
    assert len((await db.scalars(select(Usuario).where(Usuario.email == "ana@example.com"))).all()) == 1


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
