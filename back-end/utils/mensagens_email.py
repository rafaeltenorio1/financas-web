from html import escape

from utils.config import settings
from utils.email import ConteudoEmail

AVISO_NAO_FOI_VOCE = (
    "Se não foi você, troque sua senha imediatamente e confira a verificação em duas etapas."
)


def _montar(assunto: str, nome: str, paragrafos: list[str]) -> ConteudoEmail:
    texto = "\n\n".join([f"Olá, {nome}.", *paragrafos, "Finanças"])

    blocos = "".join(f'<p style="margin:0 0 16px">{escape(p)}</p>' for p in paragrafos)
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
