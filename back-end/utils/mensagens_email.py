from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from html import escape

from models.enums import TipoLembrete, TipoTransacao
from schemas.resumo import ResumoOut

from utils.config import settings
from utils.email import ConteudoEmail

AVISO_NAO_FOI_VOCE = (
    "Se não foi você, troque sua senha imediatamente e confira a verificação em duas etapas."
)


def mascarar_email(email: str) -> str:
    local, _, dominio = email.partition("@")
    return f"{local[:1]}***@{dominio}"


def _montar(
    assunto: str,
    nome: str,
    paragrafos: list[str],
    botao: tuple[str, str] | None = None,
    secoes: list[tuple[str, list[str]]] | None = None,
) -> ConteudoEmail:
    linhas_texto = [f"Olá, {nome}.", *paragrafos]
    blocos = "".join(f'<p style="margin:0 0 16px">{escape(p)}</p>' for p in paragrafos)

    for titulo, itens in secoes or []:
        linhas_texto.append("\n".join([f"{titulo}:", *(f"- {item}" for item in itens)]))
        blocos += (
            f'<h2 style="margin:24px 0 8px;font-size:16px;color:#163832">{escape(titulo)}</h2>'
            '<ul style="margin:0 0 16px;padding-left:20px">'
            + "".join(f'<li style="margin:0 0 4px">{escape(item)}</li>' for item in itens)
            + "</ul>"
        )

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


def tentativa_de_cadastro(nome: str) -> ConteudoEmail:
    base = settings.FRONT_URL.rstrip("/")
    return _montar(
        "Tentativa de cadastro com seu e-mail",
        nome,
        [
            "Alguém tentou criar uma conta no Finanças com este e-mail, que já está cadastrado. "
            "Nenhuma conta nova foi criada e nada mudou na sua.",
            f"Se foi você, é só entrar: {base}/#/entrar",
            "Se você não lembra a senha, ou se não reconhece esta conta, redefina a senha pelo botão abaixo. "
            "Isso também confirma que o e-mail é seu.",
        ],
        ("Redefinir senha", f"{base}/#/esqueci-senha"),
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


@dataclass(frozen=True)
class ItemLembrete:
    lembrete: TipoLembrete
    nome: str
    valor: Decimal
    tipo: TipoTransacao
    vencimento: date


def formatar_reais(valor: Decimal) -> str:
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "_").replace(".", ",").replace("_", ".")


def formatar_data(dia: date) -> str:
    return dia.strftime("%d/%m/%Y")


def _uma_linha(texto: str) -> str:
    return " ".join(texto.split())


def _descrever_item(item: ItemLembrete) -> str:
    natureza = "a receber" if item.tipo is TipoTransacao.RECEITA else "a pagar"
    return f"{_uma_linha(item.nome)}: {formatar_reais(item.valor)} ({natureza}, vencimento em {formatar_data(item.vencimento)})"


def _titulo_secao(lembrete: TipoLembrete, vencimento: date, hoje: date) -> str:
    if lembrete is TipoLembrete.ATRASO:
        return "Venceram ontem e ainda não foram marcadas como pagas"
    if lembrete is TipoLembrete.NO_DIA:
        return "Vencem hoje"
    dias = (vencimento - hoje).days
    if dias == 1:
        return f"Vencem amanhã ({formatar_data(vencimento)})"
    return f"Vencem em {dias} dias ({formatar_data(vencimento)})"


def _assunto_lembrete(item: ItemLembrete) -> str:
    nome = _uma_linha(item.nome)
    if item.lembrete is TipoLembrete.ATRASO:
        return f"Em atraso: {nome}"
    if item.lembrete is TipoLembrete.NO_DIA:
        return f"Vence hoje: {nome}"
    return f"Vence em breve: {nome}"


def lembrete_contas(nome: str, itens: list[ItemLembrete], hoje: date) -> ConteudoEmail:
    ordem = {TipoLembrete.ATRASO: 0, TipoLembrete.NO_DIA: 1, TipoLembrete.ANTECEDENCIA: 2}
    ordenados = sorted(itens, key=lambda i: (ordem[i.lembrete], i.vencimento, i.nome.lower()))

    secoes: list[tuple[str, list[str]]] = []
    for item in ordenados:
        titulo = _titulo_secao(item.lembrete, item.vencimento, hoje)
        if not secoes or secoes[-1][0] != titulo:
            secoes.append((titulo, []))
        secoes[-1][1].append(_descrever_item(item))

    if len(itens) == 1:
        assunto = _assunto_lembrete(itens[0])
    else:
        assunto = f"Você tem {len(itens)} lembretes de contas"

    return _montar(
        assunto,
        nome,
        [
            "Confira os lembretes das suas contas recorrentes.",
            "Quando pagar ou receber, marque a conta como paga no Finanças: o vencimento avança "
            "e os lembretes dessa data param. Você pode ajustar esses avisos nas preferências.",
        ],
        ("Abrir o Finanças", settings.FRONT_URL),
        secoes,
    )


MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def nome_do_mes(dia: date) -> str:
    return f"{MESES[dia.month - 1]} de {dia.year}"


@dataclass(frozen=True)
class ContaPrevista:
    nome: str
    valor: Decimal
    tipo: TipoTransacao
    vencimento: date


def _comparacao_despesas(atual: Decimal, anterior: Decimal, mes_anterior: date) -> str | None:
    if anterior == 0:
        return None
    nome = MESES[mes_anterior.month - 1]
    variacao = round((atual - anterior) / anterior * 100)
    if variacao > 0:
        return f"As despesas foram {variacao}% maiores que em {nome}."
    if variacao < 0:
        return f"As despesas foram {-variacao}% menores que em {nome}."
    return f"As despesas ficaram no mesmo nível de {nome}."


def resumo_mensal(
    nome: str,
    mes: date,
    resumo: ResumoOut,
    despesas_mes_anterior: Decimal,
    mes_anterior: date,
    contas: list[ContaPrevista],
    mes_seguinte: date,
) -> ConteudoEmail:
    paragrafos = [f"Veja como foi {nome_do_mes(mes)} nas suas finanças."]
    comparacao = _comparacao_despesas(resumo.despesas, despesas_mes_anterior, mes_anterior)
    if comparacao:
        paragrafos.append(comparacao)

    secoes = [
        (
            "Totais do mês",
            [f"Receitas: {formatar_reais(resumo.receitas)}", f"Despesas: {formatar_reais(resumo.despesas)}"],
        )
    ]

    maiores = [c for c in resumo.por_categoria if c.tipo is TipoTransacao.DESPESA][:5]
    if maiores:
        secoes.append(
            (
                "Onde você mais gastou",
                [
                    f"{_uma_linha(c.nome or 'Sem categoria')}: {formatar_reais(c.total)} "
                    f"({round(c.total / resumo.despesas * 100)}% das despesas)"
                    for c in maiores
                ],
            )
        )

    if contas:
        itens = [
            f"{formatar_data(c.vencimento)}: {_uma_linha(c.nome)}, {formatar_reais(c.valor)} "
            f"({'a receber' if c.tipo is TipoTransacao.RECEITA else 'a pagar'})"
            for c in contas
        ]
        a_pagar = sum((c.valor for c in contas if c.tipo is TipoTransacao.DESPESA), Decimal("0"))
        a_receber = sum((c.valor for c in contas if c.tipo is TipoTransacao.RECEITA), Decimal("0"))
        if a_pagar:
            itens.append(f"Total previsto a pagar: {formatar_reais(a_pagar)}")
        if a_receber:
            itens.append(f"Total previsto a receber: {formatar_reais(a_receber)}")
        secoes.append((f"Contas previstas para {nome_do_mes(mes_seguinte)}", itens))

    return _montar(
        f"Seu resumo de {nome_do_mes(mes)}",
        nome,
        paragrafos,
        ("Abrir o Finanças", settings.FRONT_URL),
        secoes,
    )
