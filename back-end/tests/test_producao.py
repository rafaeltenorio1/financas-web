from contextlib import asynccontextmanager

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from apoio import ORIGEM_FRONT

SEGURA = {
    "AMBIENTE": "producao",
    "COOKIE_SECURE": True,
    "SECRET_KEY": "x" * 64,
    "TOTP_CHAVE": "qualquer",
    "SMTP_SEGURANCA": "starttls",
    "FRONT_URL": "https://financas.example.com",
    "CORS_ORIGINS": ["https://financas.example.com"],
}


def _settings(**ajustes):
    from utils.config import Settings

    return Settings(**{**SEGURA, **ajustes})


@asynccontextmanager
async def _cliente(monkeypatch, ip=("127.0.0.1", 50000), **ajustes):
    from httpx import ASGITransport, AsyncClient

    from main import criar_app
    from utils.config import settings

    for nome, valor in ajustes.items():
        monkeypatch.setattr(settings, nome, valor)
    app = criar_app()

    async def eco_ip(request: Request):
        return {"ip": request.client.host}

    async def cache_proprio():
        return JSONResponse({"ok": True}, headers={"Cache-Control": "public, max-age=60"})

    app.add_api_route("/eco-ip", eco_ip, methods=["GET"])
    app.add_api_route("/cache-proprio", cache_proprio, methods=["GET"])

    async with AsyncClient(
        transport=ASGITransport(app=app, client=ip),
        base_url="http://testserver",
        headers={"Origin": ORIGEM_FRONT},
    ) as cliente:
        yield cliente


def test_configuracao_segura_e_aceita():
    assert _settings().AMBIENTE == "producao"


def test_ambiente_padrao_e_producao(monkeypatch):
    monkeypatch.delenv("AMBIENTE", raising=False)
    from utils.config import Settings

    with pytest.raises(ValidationError, match="Configuração insegura para produção"):
        Settings(COOKIE_SECURE=False)


@pytest.mark.parametrize(
    "ajuste, trecho",
    [
        ({"COOKIE_SECURE": False}, "COOKIE_SECURE"),
        ({"SECRET_KEY": "curta"}, "SECRET_KEY"),
        ({"SECRET_KEY": "troque-por-um-valor-aleatorio-bem-comprido-mesmo"}, "SECRET_KEY"),
        ({"SMTP_SEGURANCA": "nenhuma"}, "SMTP_SEGURANCA"),
        ({"FRONT_URL": "http://financas.example.com"}, "FRONT_URL"),
        ({"CORS_ORIGINS": ["*"]}, "CORS_ORIGINS"),
        ({"CORS_ORIGINS": ["http://financas.example.com"]}, "CORS_ORIGINS"),
    ],
)
def test_recusa_configuracao_insegura_em_producao(ajuste, trecho):
    with pytest.raises(ValidationError) as erro:
        _settings(**ajuste)

    assert trecho in str(erro.value)


def test_erro_de_configuracao_nao_mostra_os_segredos():
    with pytest.raises(ValidationError) as erro:
        _settings(
            SECRET_KEY="segredo-curto",
            TOTP_CHAVE="chave-totp-secreta",
            SMTP_SENHA="senha-smtp-secreta",
        )

    mensagem = str(erro.value)
    assert "SECRET_KEY precisa" in mensagem
    for segredo in ["segredo-curto", "chave-totp-secreta", "senha-smtp-secreta"]:
        assert segredo not in mensagem


def test_desenvolvimento_aceita_configuracao_local():
    configuracao = _settings(
        AMBIENTE="desenvolvimento",
        COOKIE_SECURE=False,
        SECRET_KEY="curta",
        SMTP_SEGURANCA="nenhuma",
        FRONT_URL="http://localhost:5500",
        CORS_ORIGINS=["http://localhost:5500"],
    )
    assert configuracao.AMBIENTE == "desenvolvimento"


async def test_cabecalhos_de_seguranca_em_toda_resposta(client):
    for resposta in [
        await client.get("/saude"),
        await client.get("/rota-que-nao-existe"),
        await client.get("/transacoes"),
    ]:
        assert resposta.headers["x-content-type-options"] == "nosniff"
        assert resposta.headers["x-frame-options"] == "DENY"
        assert resposta.headers["referrer-policy"] == "no-referrer"
        assert resposta.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
        assert resposta.headers["cache-control"] == "no-store"
        assert "strict-transport-security" not in resposta.headers


async def test_cabecalhos_tambem_no_preflight_do_cors(client):
    resposta = await client.options(
        "/transacoes",
        headers={"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "X-CSRF-Token"},
    )

    assert resposta.status_code == 200
    assert resposta.headers["x-frame-options"] == "DENY"


async def test_rota_pode_definir_o_proprio_cache(monkeypatch):
    async with _cliente(monkeypatch) as cliente:
        resposta = await cliente.get("/cache-proprio")

    assert resposta.headers["cache-control"] == "public, max-age=60"


async def test_documentacao_existe_em_desenvolvimento(monkeypatch):
    async with _cliente(monkeypatch, AMBIENTE="desenvolvimento") as cliente:
        docs = await cliente.get("/docs")
        assert docs.status_code == 200
        assert "content-security-policy" not in docs.headers
        assert (await cliente.get("/openapi.json")).status_code == 200


async def test_producao_desliga_a_documentacao_e_liga_o_hsts(monkeypatch):
    async with _cliente(monkeypatch, AMBIENTE="producao") as cliente:
        for caminho in ["/docs", "/redoc", "/openapi.json"]:
            assert (await cliente.get(caminho)).status_code == 404

        resposta = await cliente.get("/saude")
        assert resposta.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


async def test_sem_proxy_configurado_ignora_x_forwarded_for(monkeypatch):
    async with _cliente(monkeypatch, ip=("198.51.100.7", 40000), PROXIES_CONFIAVEIS=[]) as cliente:
        resposta = await cliente.get("/eco-ip", headers={"X-Forwarded-For": "203.0.113.9"})

    assert resposta.json() == {"ip": "198.51.100.7"}


async def test_proxy_confiavel_informa_o_ip_real(monkeypatch):
    async with _cliente(monkeypatch, ip=("10.0.0.2", 40000), PROXIES_CONFIAVEIS=["10.0.0.2"]) as cliente:
        resposta = await cliente.get("/eco-ip", headers={"X-Forwarded-For": "203.0.113.9"})

    assert resposta.json() == {"ip": "203.0.113.9"}


async def test_cliente_comum_nao_falsifica_o_ip_mesmo_com_proxy_configurado(monkeypatch):
    async with _cliente(monkeypatch, ip=("198.51.100.7", 40000), PROXIES_CONFIAVEIS=["10.0.0.2"]) as cliente:
        resposta = await cliente.get("/eco-ip", headers={"X-Forwarded-For": "203.0.113.9"})

    assert resposta.json() == {"ip": "198.51.100.7"}


async def test_proxy_confiavel_aceita_rede_inteira(monkeypatch):
    async with _cliente(monkeypatch, ip=("172.18.0.5", 40000), PROXIES_CONFIAVEIS=["172.18.0.0/16"]) as cliente:
        resposta = await cliente.get("/eco-ip", headers={"X-Forwarded-For": "203.0.113.9"})

    assert resposta.json() == {"ip": "203.0.113.9"}
