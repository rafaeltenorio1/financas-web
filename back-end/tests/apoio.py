"""Funções de apoio compartilhadas pelos testes."""

from contextlib import asynccontextmanager

ORIGEM_FRONT = "http://localhost:5500"
SENHA_PADRAO = "senha-forte-123"


@asynccontextmanager
async def criar_cliente(origem: str | None = ORIGEM_FRONT):
    """Cliente HTTP que chama a API em memória. Cada cliente tem seus próprios cookies,
    então dois clientes simulam dois navegadores (duas sessões)."""
    from httpx import ASGITransport, AsyncClient

    from main import app

    headers = {"Origin": origem} if origem else {}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", headers=headers
    ) as c:
        yield c


async def cadastrar(client, email="ana@example.com", senha=SENHA_PADRAO, nome="Ana"):
    resposta = await client.post(
        "/auth/register", json={"nome": nome, "email": email, "senha": senha}
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


async def login(client, email="ana@example.com", senha=SENHA_PADRAO):
    return await client.post("/auth/login", json={"email": email, "senha": senha})


async def obter_csrf(client) -> str:
    resposta = await client.get("/auth/csrf")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["csrf_token"]
