import logging

from apoio import SENHA_PADRAO, corpo_html, corpo_texto, marcar_verificado, obter_csrf


def _conteudo(nome="Ana"):
    from utils import mensagens_email

    return mensagens_email.senha_trocada(nome, "203.0.113.7")


async def test_monta_mensagem_com_texto_e_html():
    from utils.config import settings
    from utils.email import montar_mensagem

    mensagem = montar_mensagem("ana@example.com", _conteudo())

    assert mensagem["To"] == "ana@example.com"
    assert mensagem["From"] == settings.EMAIL_REMETENTE
    assert mensagem["Subject"] == "Sua senha foi alterada"
    assert "Olá, Ana." in corpo_texto(mensagem)
    assert "203.0.113.7" in corpo_texto(mensagem)
    assert "<h1" in corpo_html(mensagem)


async def test_html_escapa_dados_do_usuario():
    from utils.email import montar_mensagem

    nome = '<script>alert("x")</script>'
    mensagem = montar_mensagem("ana@example.com", _conteudo(nome))

    assert "<script>" not in corpo_html(mensagem)
    assert "&lt;script&gt;" in corpo_html(mensagem)
    assert nome in corpo_texto(mensagem)


async def test_starttls_com_login(caixa, monkeypatch):
    from utils.config import settings
    from utils.email import enviar_email

    monkeypatch.setattr(settings, "SMTP_SEGURANCA", "starttls")
    monkeypatch.setattr(settings, "SMTP_USUARIO", "remetente@example.com")
    monkeypatch.setattr(settings, "SMTP_SENHA", "senha-smtp")

    assert await enviar_email("ana@example.com", _conteudo()) is True

    conexao = caixa.conexoes[0]
    assert not conexao.ssl
    assert conexao.starttls_usado
    assert conexao.login_usado == ("remetente@example.com", "senha-smtp")
    assert len(caixa.mensagens) == 1


async def test_ssl_usa_smtp_ssl(caixa, monkeypatch):
    from utils.config import settings
    from utils.email import enviar_email

    monkeypatch.setattr(settings, "SMTP_SEGURANCA", "ssl")

    assert await enviar_email("ana@example.com", _conteudo()) is True

    conexao = caixa.conexoes[0]
    assert conexao.ssl
    assert not conexao.starttls_usado


async def test_sem_seguranca_e_sem_usuario_nao_faz_starttls_nem_login(caixa, monkeypatch):
    from utils.config import settings
    from utils.email import enviar_email

    monkeypatch.setattr(settings, "SMTP_SEGURANCA", "nenhuma")
    monkeypatch.setattr(settings, "SMTP_USUARIO", "")

    assert await enviar_email("ana@example.com", _conteudo()) is True

    conexao = caixa.conexoes[0]
    assert not conexao.starttls_usado
    assert conexao.login_usado is None


async def test_falha_no_smtp_devolve_false_e_nao_vaza_dados_no_log(caixa, caplog):
    from utils.email import enviar_email

    caixa.falhar = True
    with caplog.at_level(logging.ERROR):
        assert await enviar_email("ana@example.com", _conteudo()) is False

    assert "SMTPServerDisconnected" in caplog.text
    assert "ana@example.com" not in caplog.text
    assert "Olá" not in caplog.text


async def test_falha_no_smtp_nao_quebra_a_rota(logado, caixa):
    await marcar_verificado()
    await caixa.esvaziar()
    caixa.falhar = True
    csrf = await obter_csrf(logado)

    resposta = await logado.post(
        "/auth/trocar-senha",
        json={"senha_atual": SENHA_PADRAO, "senha_nova": "outra-senha-456"},
        headers={"X-CSRF-Token": csrf},
    )

    assert resposta.status_code == 200
    assert await caixa.recebidos() == []
    assert len(caixa.conexoes) == 1
