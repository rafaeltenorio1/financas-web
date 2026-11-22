import asyncio
from datetime import datetime, timezone

import pytest

from apoio import (
    cadastrar,
    corpo_html,
    corpo_texto,
    criar_cliente,
    login,
    marcar_verificado,
    obter_csrf,
)

AGORA = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)


async def _conta(client, data_inicio, **campos):
    corpo = {
        "nome": "Aluguel",
        "valor": "1500.00",
        "tipo": "despesa",
        "periodicidade": "mensal",
        "data_inicio": data_inicio,
        **campos,
    }
    csrf = await obter_csrf(client)
    resposta = await client.post("/contas-recorrentes", json=corpo, headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


async def _preferencias(client, **campos):
    csrf = await obter_csrf(client)
    resposta = await client.patch("/auth/me", json=campos, headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == 200, resposta.text


async def _rodar(db, agora=AGORA):
    from utils.lembretes import enviar_lembretes

    return await enviar_lembretes(db, agora)


@pytest.fixture
async def logado(logado, caixa):
    await marcar_verificado()
    await caixa.esvaziar()
    return logado


async def test_avisa_um_dia_antes_por_padrao(logado, caixa, db):
    await _conta(logado, "2026-11-23")

    assert await _rodar(db) == 1

    mensagens = await caixa.recebidos()
    assert [m["Subject"] for m in mensagens] == ["Vence em breve: Aluguel"]
    assert mensagens[0]["To"] == "ana@example.com"
    texto = corpo_texto(mensagens[0])
    assert "Vencem amanhã (23/11/2026)" in texto
    assert "Aluguel: R$ 1.500,00 (a pagar, vencimento em 23/11/2026)" in texto


async def test_avisa_no_dia(logado, caixa, db):
    await _conta(logado, "2026-11-22")

    await _rodar(db)

    assert await caixa.assuntos() == ["Vence hoje: Aluguel"]


async def test_avisa_atraso_no_dia_seguinte(logado, caixa, db):
    await _conta(logado, "2026-11-21")

    await _rodar(db)

    mensagens = await caixa.recebidos()
    assert [m["Subject"] for m in mensagens] == ["Em atraso: Aluguel"]
    assert "Venceram ontem e ainda não foram marcadas como pagas" in corpo_texto(mensagens[0])


async def test_nao_avisa_fora_das_datas(logado, caixa, db):
    await _conta(logado, "2026-11-20")
    await _conta(logado, "2026-11-25")

    assert await _rodar(db) == 0
    assert await caixa.recebidos() == []


async def test_agrupa_as_contas_em_um_email_e_detalha_cada_uma(logado, caixa, db):
    await _conta(logado, "2026-11-21", nome="Internet", valor="99.90")
    await _conta(logado, "2026-11-22", nome="Aluguel", valor="1500.00")
    await _conta(logado, "2026-11-22", nome="Condomínio", valor="650.00")
    await _conta(logado, "2026-11-23", nome="Salário", valor="5000.00", tipo="receita")

    assert await _rodar(db) == 1

    mensagens = await caixa.recebidos()
    assert len(mensagens) == 1
    assert mensagens[0]["Subject"] == "Você tem 4 lembretes de contas"
    texto = corpo_texto(mensagens[0])
    linhas_esperadas = [
        "Venceram ontem e ainda não foram marcadas como pagas:",
        "- Internet: R$ 99,90 (a pagar, vencimento em 21/11/2026)",
        "Vencem hoje:",
        "- Aluguel: R$ 1.500,00 (a pagar, vencimento em 22/11/2026)",
        "- Condomínio: R$ 650,00 (a pagar, vencimento em 22/11/2026)",
        "Vencem amanhã (23/11/2026):",
        "- Salário: R$ 5.000,00 (a receber, vencimento em 23/11/2026)",
    ]
    posicoes = [texto.index(linha) for linha in linhas_esperadas]
    assert posicoes == sorted(posicoes)
    html = corpo_html(mensagens[0])
    assert html.count("<li") == 4


async def test_nao_repete_o_mesmo_lembrete(logado, caixa, db):
    await _conta(logado, "2026-11-22")

    assert await _rodar(db) == 1
    assert await _rodar(db) == 0
    assert await _rodar(db, AGORA.replace(hour=20)) == 0

    assert len(await caixa.recebidos()) == 1


async def test_cada_etapa_avisa_uma_vez(logado, caixa, db):
    await _conta(logado, "2026-11-23")

    await _rodar(db, datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc))
    await _rodar(db, datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc))
    await _rodar(db, datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc))
    await _rodar(db, datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc))

    assert await caixa.assuntos() == [
        "Vence em breve: Aluguel",
        "Vence hoje: Aluguel",
        "Em atraso: Aluguel",
    ]


async def test_nao_envia_antes_da_hora_local(logado, caixa, db):
    await _conta(logado, "2026-11-22")

    assert await _rodar(db, datetime(2026, 11, 22, 10, 59, tzinfo=timezone.utc)) == 0
    assert await _rodar(db, datetime(2026, 11, 22, 11, 0, tzinfo=timezone.utc)) == 1


async def test_usa_o_fuso_do_usuario(logado, caixa, db):
    await _preferencias(logado, fuso="Asia/Tokyo")
    await _conta(logado, "2026-11-23")

    assert await _rodar(db, datetime(2026, 11, 22, 21, 0, tzinfo=timezone.utc)) == 0
    assert await _rodar(db, datetime(2026, 11, 23, 0, 0, tzinfo=timezone.utc)) == 1

    assert await caixa.assuntos() == ["Vence hoje: Aluguel"]


async def test_respeita_dias_de_antecedencia(logado, caixa, db):
    await _preferencias(logado, lembrete_dias_antes=3)
    await _conta(logado, "2026-11-23", nome="Amanhã")
    await _conta(logado, "2026-11-25", nome="Daqui a três dias")

    await _rodar(db)

    mensagens = await caixa.recebidos()
    assert [m["Subject"] for m in mensagens] == ["Vence em breve: Daqui a três dias"]
    assert "Vencem em 3 dias (25/11/2026)" in corpo_texto(mensagens[0])


async def test_preferencias_desligadas_nao_enviam(logado, caixa, db):
    await _preferencias(logado, lembrete_dias_antes=0, lembrete_no_dia=False, lembrete_atraso=False)
    for data in ["2026-11-21", "2026-11-22", "2026-11-23"]:
        await _conta(logado, data)

    assert await _rodar(db) == 0


async def test_conta_silenciada_ou_inativa_nao_avisa(logado, caixa, db):
    silenciada = await _conta(logado, "2026-11-22", avisar=False)
    inativa = await _conta(logado, "2026-11-22", nome="Academia")
    csrf = await obter_csrf(logado)
    await logado.patch(
        f"/contas-recorrentes/{inativa['id_conta_recorrente']}",
        json={"ativa": False},
        headers={"X-CSRF-Token": csrf},
    )

    assert silenciada["avisar"] is False
    assert await _rodar(db) == 0


async def test_conta_paga_para_de_avisar(logado, caixa, db):
    conta = await _conta(logado, "2026-11-22")
    csrf = await obter_csrf(logado)
    await logado.post(
        f"/contas-recorrentes/{conta['id_conta_recorrente']}/pagar",
        headers={"X-CSRF-Token": csrf},
    )

    assert await _rodar(db) == 0


async def test_email_nao_verificado_nao_recebe(client, caixa, db):
    await cadastrar(client)
    await login(client)
    await _conta(client, "2026-11-22")
    await caixa.esvaziar()

    assert await _rodar(db) == 0
    assert await caixa.recebidos() == []


async def test_cada_usuario_recebe_so_as_proprias_contas(logado, caixa, db):
    await _conta(logado, "2026-11-22", nome="Aluguel da Ana")
    async with criar_cliente() as bia:
        await cadastrar(bia, email="bia@example.com", nome="Bia")
        await login(bia, email="bia@example.com")
        await marcar_verificado("bia@example.com")
        await _conta(bia, "2026-11-22", nome="Aluguel da Bia")
    await caixa.esvaziar()

    assert await _rodar(db) == 2

    por_destino = {m["To"]: corpo_texto(m) for m in await caixa.recebidos()}
    assert "Aluguel da Ana" in por_destino["ana@example.com"]
    assert "Aluguel da Bia" not in por_destino["ana@example.com"]
    assert "Aluguel da Bia" in por_destino["bia@example.com"]


async def test_falha_no_envio_nao_reenvia(logado, caixa, db):
    await _conta(logado, "2026-11-22")
    caixa.falhar = True

    assert await _rodar(db) == 0

    caixa.falhar = False
    assert await _rodar(db) == 0
    assert await caixa.recebidos() == []


async def test_nome_da_conta_e_escapado_e_nao_quebra_o_assunto(logado, caixa, db):
    await _conta(logado, "2026-11-22", nome="<b>Luz</b>\nBcc: intruso@example.com")

    assert await _rodar(db) == 1

    mensagem = (await caixa.recebidos())[0]
    assert mensagem["Bcc"] is None
    assert "\n" not in mensagem["Subject"]
    assert "<b>Luz</b>" not in corpo_html(mensagem)
    assert "&lt;b&gt;Luz&lt;/b&gt;" in corpo_html(mensagem)


async def test_laco_continua_depois_de_uma_falha(monkeypatch):
    import utils.lembretes
    from utils.config import settings

    chamadas = 0
    segunda_chamada = asyncio.Event()

    async def lembretes_falsos(db, agora):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            raise RuntimeError("banco fora do ar")
        segunda_chamada.set()
        return 0

    monkeypatch.setattr(utils.lembretes, "enviar_lembretes", lembretes_falsos)
    monkeypatch.setattr(settings, "LEMBRETES_INTERVALO_MIN", 0)

    tarefa = asyncio.create_task(utils.lembretes.executar_lembretes_periodicos())
    await asyncio.wait_for(segunda_chamada.wait(), timeout=5)
    tarefa.cancel()

    with pytest.raises(asyncio.CancelledError):
        await tarefa
    assert chamadas >= 2
