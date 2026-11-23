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
    assert resposta.status_code == 202, resposta.text
    return resposta.json()


async def login(client, email="ana@example.com", senha=SENHA_PADRAO, lembrar=None):
    dados = {"email": email, "senha": senha}
    if lembrar is not None:
        dados["lembrar"] = lembrar
    return await client.post("/auth/login", json=dados)


async def obter_csrf(client) -> str:
    resposta = await client.get("/auth/csrf")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["csrf_token"]


class ConexaoSMTPFalsa:
    def __init__(self, caixa, host, porta, ssl=False, **kwargs):
        self.caixa = caixa
        self.host = host
        self.porta = porta
        self.ssl = ssl
        self.starttls_usado = False
        self.login_usado = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.starttls_usado = True

    def login(self, usuario, senha):
        self.login_usado = (usuario, senha)

    def send_message(self, mensagem):
        if self.caixa.falhar:
            import smtplib

            raise smtplib.SMTPServerDisconnected("conexão perdida")
        self.caixa.mensagens.append(mensagem)


class CaixaDeSaida:
    def __init__(self):
        self.mensagens = []
        self.conexoes = []
        self.falhar = False

    def _conectar(self, host, porta, ssl=False, **kwargs):
        conexao = ConexaoSMTPFalsa(self, host, porta, ssl=ssl, **kwargs)
        self.conexoes.append(conexao)
        return conexao

    def smtp(self, host, porta, **kwargs):
        return self._conectar(host, porta, **kwargs)

    def smtp_ssl(self, host, porta, **kwargs):
        return self._conectar(host, porta, ssl=True, **kwargs)

    async def recebidos(self):
        from utils.email import aguardar_envios

        await aguardar_envios()
        return self.mensagens

    async def assuntos(self):
        return [m["Subject"] for m in await self.recebidos()]

    async def esvaziar(self):
        await self.recebidos()
        self.mensagens.clear()
        self.conexoes.clear()

    async def token_enviado(self, para: str) -> str:
        import re

        for mensagem in reversed(await self.recebidos()):
            if mensagem["To"] == para:
                encontrado = re.search(r"[?&]token=([A-Za-z0-9_-]+)", corpo_texto(mensagem))
                if encontrado:
                    return encontrado.group(1)
        raise AssertionError(f"nenhum link com token enviado para {para}")


def corpo_texto(mensagem) -> str:
    return mensagem.get_body(preferencelist=("plain",)).get_content()


def corpo_html(mensagem) -> str:
    return mensagem.get_body(preferencelist=("html",)).get_content()


async def marcar_verificado(email="ana@example.com"):
    import database
    from sqlalchemy import func, update

    from models.usuario import Usuario

    async with database.SessionLocal() as db:
        await db.execute(
            update(Usuario).where(Usuario.email == email).values(email_verificado_em=func.now())
        )
        await db.commit()
