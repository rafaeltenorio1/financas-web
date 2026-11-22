"""Infraestrutura dos testes.

Um Postgres descartável (testcontainers) sobe uma vez por execução do pytest,
recebe as migrações do Alembic e é destruído no final. O banco de
desenvolvimento nunca é tocado.

Importante: `database.py` e `utils/config.py` leem as variáveis de ambiente no
momento do import. Por isso o container sobe em `pytest_configure`, que roda
antes de o pytest importar os arquivos de teste, e nenhum módulo da aplicação
é importado no topo deste arquivo.
"""

import os
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from testcontainers.community.postgres import PostgresContainer

from apoio import ORIGEM_FRONT, CaixaDeSaida, cadastrar, criar_cliente, login

RAIZ_BACKEND = Path(__file__).resolve().parent.parent

_container: PostgresContainer | None = None


def pytest_configure(config):
    global _container

    _container = PostgresContainer("postgres:17", driver=None)
    _container.start()

    os.environ.update(
        POSTGRES_HOST=_container.get_container_host_ip(),
        POSTGRES_PORT=str(_container.get_exposed_port(5432)),
        POSTGRES_USER=_container.username,
        POSTGRES_PASSWORD=_container.password,
        POSTGRES_DB=_container.dbname,
        SECRET_KEY="chave-so-para-testes",
        TOTP_CHAVE=Fernet.generate_key().decode(),
        # O cliente de teste usa http; com Secure o cookie não seria reenviado.
        COOKIE_SECURE="false",
        CORS_ORIGINS=f'["{ORIGEM_FRONT}"]',
    )

    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(str(RAIZ_BACKEND / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    command.upgrade(alembic_cfg, "head")

    # NullPool: cada sessão abre e fecha a própria conexão. Evita reaproveitar
    # conexões criadas em outro event loop entre testes.
    import database
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    database.engine = create_async_engine(database.URL, poolclass=NullPool)
    database.SessionLocal = async_sessionmaker(database.engine, expire_on_commit=False)


def pytest_unconfigure(config):
    if _container is not None:
        _container.stop()


@pytest.fixture(autouse=True)
async def limpar_banco():
    """Apaga os dados criados por cada teste, preservando as categorias padrão."""
    yield
    import database
    from sqlalchemy import text

    async with database.engine.begin() as conn:
        await conn.execute(text("DELETE FROM log_tentativa"))
        # O ON DELETE CASCADE remove sessões, transações e categorias do usuário.
        await conn.execute(text("DELETE FROM usuario"))


@pytest.fixture(autouse=True)
async def caixa(monkeypatch):
    import smtplib

    from utils.email import aguardar_envios

    caixa = CaixaDeSaida()
    monkeypatch.setattr(smtplib, "SMTP", caixa.smtp)
    monkeypatch.setattr(smtplib, "SMTP_SSL", caixa.smtp_ssl)
    yield caixa
    await aguardar_envios()


@pytest.fixture
async def db():
    """Sessão direta no banco, para preparar cenários e conferir resultados."""
    import database

    async with database.SessionLocal() as sessao:
        yield sessao


@pytest.fixture
async def client():
    """Cliente HTTP que chama a API em memória, como se fosse o front-end."""
    async with criar_cliente() as c:
        yield c


@pytest.fixture
async def logado(client):
    """Cliente com usuário cadastrado e sessão ativa."""
    await cadastrar(client)
    resposta = await login(client)
    assert resposta.status_code == 200, resposta.text
    return client
