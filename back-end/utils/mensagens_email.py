from html import escape

from utils.config import settings
from utils.email import ConteudoEmail

AVISO_NAO_FOI_VOCE = (
    "Se não foi você, troque sua senha imediatamente e confira a verificação em duas etapas."
)


def mascarar_email(email: str) -> str:
    local, _, dominio = email.partition("@")
    return f"{local[:1]}***@{dominio}"


def _montar(
    assunto: str, nome: str, paragrafos: list[str], botao: tuple[str, str] | None = None
) -> ConteudoEmail:
    linhas_texto = [f"Olá, {nome}.", *paragrafos]
    blocos = "".join(f'<p style="margin:0 0 16px">{escape(p)}</p>' for p in paragrafos)

    if botao is not None:
        rotulo, link = botao
        linhas_texto.append(f"{rotulo}: {link}")
        blocos += (
            f'<p style="margin:24px 0"><a href="{escape(link)}" style="background:#235347;'
            'color:#DAF1DE;padding:12px 20px;border-radius:8px;text-decoration:none;'
            f'font-weight:600">{escape(rotulo)}</a></p>'
            '<p style="margin:0 0 16px;font-size:12px;color:#235347">'
            f"Se o botão não funcionar, copie este endereço no navegador: {escape(link)}</p>"
        )

    texto = "\n\n".join([*linhas_texto, "Finanças"])
    html = (
        '<!doctype html><html lang="pt-BR"><body style="margin:0;padding:24px;'
        "background:#DAF1DE;font-family:'Plus Jakarta Sans',Arial,sans-serif;color:#051F20\">"
        '<div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:12px;'
        'padding:24px;border-top:6px solid #235347">'
        f'<h1 style="margin:0 0 16px;font-size:20px;color:#163832">{escape(assunto)}</h1>'
        f'<p style="margin:0 0 16px">Olá, {escape(nome)}.</p>'
        f"{blocos}"
        '<p style="margin:24px 0 0;font-size:12px;color:#235347">Finanças</p>'
        "</div></body></html>"
    )
    return ConteudoEmail(assunto=assunto, texto=texto, html=html)


def _alerta(assunto: str, nome: str, acontecimento: str, ip: str) -> ConteudoEmail:
    return _montar(
        assunto,
        nome,
        [acontecimento, f"Origem da solicitação: IP {ip}.", AVISO_NAO_FOI_VOCE],
    )


def senha_trocada(nome: str, ip: str) -> ConteudoEmail:
    return _alerta(
        "Sua senha foi alterada",
        nome,
        "A senha da sua conta foi alterada e as outras sessões abertas foram encerradas.",
        ip,
    )


def dois_fatores_ativado(nome: str, ip: str) -> ConteudoEmail:
    return _alerta(
        "Verificação em duas etapas ativada",
        nome,
        "A verificação em duas etapas foi ativada na sua conta e as outras sessões foram encerradas.",
        ip,
    )


def dois_fatores_desativado(nome: str, ip: str) -> ConteudoEmail:
    return _alerta(
        "Verificação em duas etapas desativada",
        nome,
        "A verificação em duas etapas foi desativada na sua conta. "
        "Agora basta a senha para entrar.",
        ip,
    )


def codigos_recuperacao_gerados(nome: str, ip: str) -> ConteudoEmail:
    return _alerta(
        "Novos códigos de recuperação",
        nome,
        "Novos códigos de recuperação foram gerados e os anteriores deixaram de valer.",
        ip,
    )


def conta_excluida(nome: str, ip: str) -> ConteudoEmail:
    return _montar(
        "Sua conta foi excluída",
        nome,
        [
            "Sua conta e todos os dados registrados nela foram excluídos.",
            f"Origem da solicitação: IP {ip}.",
            "Se não foi você, alguém conhecia sua senha: troque-a nos outros serviços "
            "em que você a usa.",
        ],
    )


def bloqueio_por_tentativas(nome: str) -> ConteudoEmail:
    return _montar(
        "Tentativas de acesso bloqueadas",
        nome,
        [
            "Houve várias tentativas seguidas com senha ou código incorretos na sua conta. "
            f"Por segurança, novas tentativas ficam bloqueadas por {settings.LOGIN_JANELA_MIN} minutos.",
            "Se foi você, aguarde e tente de novo. Se não foi, alguém pode estar tentando "
            "adivinhar sua senha: troque-a assim que conseguir entrar e ative a verificação "
            "em duas etapas.",
        ],
    )


def verificacao_email(nome: str, link: str) -> ConteudoEmail:
    return _montar(
        "Confirme seu e-mail",
        nome,
        [
            "Confirme que este endereço é seu para receber avisos e lembretes do Finanças. "
            f"O link vale por {settings.TOKEN_VERIFICACAO_HORAS} horas.",
            "Se você não criou uma conta, ignore este e-mail.",
        ],
        ("Confirmar e-mail", link),
    )


def redefinir_senha(nome: str, link: str) -> ConteudoEmail:
    return _montar(
        "Redefinição de senha",
        nome,
        [
            "Recebemos um pedido para redefinir a senha da sua conta. "
            f"O link vale por {settings.TOKEN_REDEFINIR_SENHA_MIN} minutos e só pode ser usado uma vez.",
            "Se não foi você, ignore este e-mail: sua senha continua a mesma.",
        ],
        ("Redefinir senha", link),
    )


def senha_redefinida(nome: str, ip: str) -> ConteudoEmail:
    return _alerta(
        "Sua senha foi redefinida",
        nome,
        "A senha da sua conta foi redefinida pelo link enviado por e-mail "
        "e todas as sessões abertas foram encerradas.",
        ip,
    )


def confirmar_troca_email(nome: str, link: str) -> ConteudoEmail:
    return _montar(
        "Confirme seu novo e-mail",
        nome,
        [
            "Recebemos um pedido para usar este endereço na sua conta do Finanças. "
            f"O link vale por {settings.TOKEN_TROCAR_EMAIL_MIN} minutos.",
            "Se você não pediu essa troca, ignore este e-mail.",
        ],
        ("Confirmar novo e-mail", link),
    )


def troca_email_solicitada(nome: str, email_novo: str, ip: str) -> ConteudoEmail:
    return _alerta(
        "Pedido de troca de e-mail",
        nome,
        f"Foi pedida a troca do e-mail da sua conta para {mascarar_email(email_novo)}. "
        "A troca só acontece depois da confirmação no novo endereço.",
        ip,
    )


def email_trocado(nome: str, email_novo: str, ip: str) -> ConteudoEmail:
    return _alerta(
        "O e-mail da sua conta foi trocado",
        nome,
        f"O e-mail da sua conta agora é {mascarar_email(email_novo)}. "
        "Os próximos avisos irão para o novo endereço.",
        ip,
    )
