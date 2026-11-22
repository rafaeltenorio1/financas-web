import asyncio
import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage

from utils.config import settings

logger = logging.getLogger(__name__)

_pendentes: set[asyncio.Task] = set()


@dataclass(frozen=True)
class ConteudoEmail:
    assunto: str
    texto: str
    html: str


def montar_mensagem(destinatario: str, conteudo: ConteudoEmail) -> EmailMessage:
    mensagem = EmailMessage()
    mensagem["From"] = settings.EMAIL_REMETENTE
    mensagem["To"] = destinatario
    mensagem["Subject"] = conteudo.assunto
    mensagem.set_content(conteudo.texto)
    mensagem.add_alternative(conteudo.html, subtype="html")
    return mensagem


def _enviar_smtp(mensagem: EmailMessage) -> None:
    contexto = ssl.create_default_context()
    if settings.SMTP_SEGURANCA == "ssl":
        servidor = smtplib.SMTP_SSL(
            settings.SMTP_HOST, settings.SMTP_PORTA, timeout=settings.SMTP_TIMEOUT_S, context=contexto
        )
    else:
        servidor = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORTA, timeout=settings.SMTP_TIMEOUT_S)

    with servidor:
        if settings.SMTP_SEGURANCA == "starttls":
            servidor.starttls(context=contexto)
        if settings.SMTP_USUARIO:
            servidor.login(settings.SMTP_USUARIO, settings.SMTP_SENHA)
        servidor.send_message(mensagem)


async def enviar_email(destinatario: str, conteudo: ConteudoEmail) -> bool:
    try:
        await asyncio.to_thread(_enviar_smtp, montar_mensagem(destinatario, conteudo))
    except Exception as erro:
        logger.error("Falha ao enviar e-mail (%s).", type(erro).__name__)
        return False
    return True


def agendar_envio(destinatario: str, conteudo: ConteudoEmail) -> None:
    tarefa = asyncio.create_task(enviar_email(destinatario, conteudo))
    _pendentes.add(tarefa)
    tarefa.add_done_callback(_pendentes.discard)


async def aguardar_envios(timeout: float | None = None) -> None:
    if _pendentes:
        await asyncio.wait(set(_pendentes), timeout=timeout)
