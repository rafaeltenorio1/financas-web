from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CABECALHOS_FIXOS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}
POLITICA_DE_CONTEUDO = "default-src 'none'; frame-ancestors 'none'"
HSTS = "max-age=31536000; includeSubDomains"
CAMINHOS_DA_DOCUMENTACAO = ("/docs", "/redoc")


class CabecalhosDeSeguranca:
    def __init__(self, app: ASGIApp, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        documentacao = scope["path"].startswith(CAMINHOS_DA_DOCUMENTACAO)

        async def enviar(mensagem: Message) -> None:
            if mensagem["type"] == "http.response.start":
                cabecalhos = MutableHeaders(scope=mensagem)
                for nome, valor in CABECALHOS_FIXOS.items():
                    cabecalhos.setdefault(nome, valor)
                if not documentacao:
                    cabecalhos.setdefault("Content-Security-Policy", POLITICA_DE_CONTEUDO)
                if self.hsts:
                    cabecalhos.setdefault("Strict-Transport-Security", HSTS)
            await send(mensagem)

        await self.app(scope, receive, enviar)
