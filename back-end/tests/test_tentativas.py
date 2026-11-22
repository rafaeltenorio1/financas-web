from apoio import cadastrar, login


async def test_bloqueia_email_apos_max_falhas_mesmo_com_senha_certa(client):
    from utils.config import settings

    await cadastrar(client)
    for _ in range(settings.LOGIN_MAX_FALHAS):
        assert (await login(client, senha="senha-errada-1")).status_code == 401

    resposta = await login(client)

    assert resposta.status_code == 429
    assert resposta.headers["retry-after"] == str(settings.LOGIN_JANELA_MIN * 60)


async def test_sucesso_zera_contagem_do_email(client):
    from utils.config import settings

    await cadastrar(client)
    for _ in range(settings.LOGIN_MAX_FALHAS - 1):
        await login(client, senha="senha-errada-1")
    assert (await login(client)).status_code == 200

    # Depois do sucesso, as falhas anteriores não contam mais.
    for _ in range(settings.LOGIN_MAX_FALHAS - 1):
        await login(client, senha="senha-errada-1")
    assert (await login(client)).status_code == 200


async def test_falhas_antigas_fora_da_janela_nao_contam(client, db):
    from sqlalchemy import update

    from models.log_tentativa import LogTentativa
    from utils.config import settings

    await cadastrar(client)
    for _ in range(settings.LOGIN_MAX_FALHAS):
        await login(client, senha="senha-errada-1")

    # Empurra as falhas para antes do início da janela.
    from datetime import datetime, timedelta, timezone

    antes = datetime.now(timezone.utc) - timedelta(minutes=settings.LOGIN_JANELA_MIN + 1)
    await db.execute(update(LogTentativa).values(ocorrida_em=antes))
    await db.commit()

    assert (await login(client)).status_code == 200


async def test_bloqueia_ip_que_tenta_muitos_emails(client):
    from utils.config import settings

    await cadastrar(client, email="alvo@example.com")
    for i in range(settings.LOGIN_MAX_FALHAS_IP):
        await login(client, email=f"chute{i}@example.com", senha="senha-errada-1")

    # O e-mail alvo nunca falhou, mas o IP passou do limite.
    resposta = await login(client, email="alvo@example.com")
    assert resposta.status_code == 429


async def test_front_consegue_ler_o_tempo_de_espera_do_bloqueio(client):
    from utils.config import settings

    await cadastrar(client)
    for _ in range(settings.LOGIN_MAX_FALHAS):
        await login(client, senha="senha-errada-1")

    resposta = await login(client)

    assert resposta.status_code == 429
    assert "retry-after" in resposta.headers["access-control-expose-headers"].lower()
