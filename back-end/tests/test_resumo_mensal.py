import asyncio
from datetime import datetime, timezone

import pytest

from apoio import cadastrar, corpo_html, corpo_texto, login, marcar_verificado, obter_csrf

AGORA = datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)


async def _post(client, url, corpo):
    csrf = await obter_csrf(client)
    resposta = await client.post(url, json=corpo, headers={"X-CSRF-Token": csrf})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


async def _transacao(client, valor, data_hora, tipo="despesa", id_categoria=None):
    return await _post(
        client,
        "/transacoes",
        {"valor": valor, "data_hora": data_hora, "tipo": tipo, "id_categoria": id_categoria},
    )


async def _categoria(client, nome):
    return (await _post(client, "/categorias", {"nome": nome, "tipo_padrao": "despesa"}))["id_categoria"]


async def _rodar(db, agora=AGORA):
    from utils.resumo_mensal import enviar_resumos

    return await enviar_resumos(db, agora)


async def _texto_unico(caixa):
    mensagens = await caixa.recebidos()
    assert len(mensagens) == 1
    return mensagens[0], corpo_texto(mensagens[0])


@pytest.fixture
async def logado(logado, caixa):
    await marcar_verificado()
    await caixa.esvaziar()
    return logado


async def test_envia_totais_do_mes_sem_saldo(logado, caixa, db):
    mercado = await _categoria(logado, "Mercado")
    await _transacao(logado, "5000.00", "2026-11-05T12:00:00-03:00", tipo="receita")
    await _transacao(logado, "800.00", "2026-11-10T12:00:00-03:00", id_categoria=mercado)
    await _transacao(logado, "200.00", "2026-11-20T12:00:00-03:00")

    assert await _rodar(db) == 1

    mensagem, texto = await _texto_unico(caixa)
    assert mensagem["Subject"] == "Seu resumo de novembro de 2026"
    assert mensagem["To"] == "ana@example.com"
    assert "Receitas: R$ 5.000,00" in texto
    assert "Despesas: R$ 1.000,00" in texto
    assert "saldo" not in texto.lower()
    assert "saldo" not in corpo_html(mensagem).lower()
    assert "4.000,00" not in texto


async def test_lista_as_cinco_categorias_com_mais_despesa(logado, caixa, db):
    valores = {"Casa A": "1500", "Feira B": "800", "Passeio C": "300", "Remédio D": "200", "Gato E": "150", "Sebo F": "50"}
    for nome, valor in valores.items():
        await _transacao(logado, valor, "2026-11-10T12:00:00-03:00", id_categoria=await _categoria(logado, nome))
    await _transacao(logado, "1000", "2026-11-10T12:00:00-03:00")

    await _rodar(db)

    _, texto = await _texto_unico(caixa)
    secao = texto.split("Onde você mais gastou:")[1]
    linhas = [l for l in secao.split("\n") if l.startswith("- ")][:5]
    assert linhas == [
        "- Casa A: R$ 1.500,00 (38% das despesas)",
        "- Sem categoria: R$ 1.000,00 (25% das despesas)",
        "- Feira B: R$ 800,00 (20% das despesas)",
        "- Passeio C: R$ 300,00 (8% das despesas)",
        "- Remédio D: R$ 200,00 (5% das despesas)",
    ]
    assert "Gato E" not in texto
    assert "Sebo F" not in texto


@pytest.mark.parametrize(
    "outubro, frase",
    [
        ("500.00", "As despesas foram 100% maiores que em outubro."),
        ("2000.00", "As despesas foram 50% menores que em outubro."),
        ("1000.00", "As despesas ficaram no mesmo nível de outubro."),
    ],
)
async def test_compara_com_o_mes_anterior(logado, caixa, db, outubro, frase):
    await _transacao(logado, outubro, "2026-10-15T12:00:00-03:00")
    await _transacao(logado, "1000.00", "2026-11-15T12:00:00-03:00")

    await _rodar(db)

    _, texto = await _texto_unico(caixa)
    assert frase in texto


async def test_sem_mes_anterior_nao_compara(logado, caixa, db):
    await _transacao(logado, "1000.00", "2026-11-15T12:00:00-03:00")

    await _rodar(db)

    _, texto = await _texto_unico(caixa)
    assert "As despesas" not in texto


async def test_lista_contas_previstas_para_o_mes_que_comeca(logado, caixa, db):
    await _transacao(logado, "100.00", "2026-11-15T12:00:00-03:00")
    base = {"periodicidade": "mensal", "tipo": "despesa"}
    await _post(logado, "/contas-recorrentes", {**base, "nome": "Aluguel", "valor": "1500.00", "data_inicio": "2026-12-10"})
    await _post(logado, "/contas-recorrentes", {**base, "nome": "Salário", "valor": "5000.00", "tipo": "receita", "data_inicio": "2026-12-05"})
    await _post(logado, "/contas-recorrentes", {**base, "nome": "Seguro", "valor": "90.00", "data_inicio": "2027-01-03"})
    inativa = await _post(logado, "/contas-recorrentes", {**base, "nome": "Academia", "valor": "120.00", "data_inicio": "2026-12-15"})
    csrf = await obter_csrf(logado)
    await logado.patch(
        f"/contas-recorrentes/{inativa['id_conta_recorrente']}",
        json={"ativa": False},
        headers={"X-CSRF-Token": csrf},
    )

    await _rodar(db)

    _, texto = await _texto_unico(caixa)
    secao = texto.split("Contas previstas para dezembro de 2026:")[1]
    assert secao.split("\n")[1:5] == [
        "- 05/12/2026: Salário, R$ 5.000,00 (a receber)",
        "- 10/12/2026: Aluguel, R$ 1.500,00 (a pagar)",
        "- Total previsto a pagar: R$ 1.500,00",
        "- Total previsto a receber: R$ 5.000,00",
    ]
    assert "Seguro" not in texto
    assert "Academia" not in texto


async def test_limites_do_mes_seguem_o_fuso_do_usuario(logado, caixa, db):
    await _transacao(logado, "100.00", "2026-11-01T02:00:00Z")
    await _transacao(logado, "300.00", "2026-12-01T02:00:00Z")

    await _rodar(db)

    _, texto = await _texto_unico(caixa)
    assert "Despesas: R$ 300,00" in texto
    assert "As despesas foram 200% maiores que em outubro." in texto


async def test_mes_sem_transacoes_nao_envia(logado, caixa, db):
    await _transacao(logado, "100.00", "2026-10-15T12:00:00-03:00")

    assert await _rodar(db) == 0
    assert await caixa.recebidos() == []


async def test_envia_uma_vez_por_mes(logado, caixa, db):
    await _transacao(logado, "100.00", "2026-11-15T12:00:00-03:00")

    assert await _rodar(db) == 1
    assert await _rodar(db) == 0
    assert await _rodar(db, datetime(2026, 12, 2, 12, 0, tzinfo=timezone.utc)) == 0

    assert len(await caixa.recebidos()) == 1


async def test_proximo_mes_envia_de_novo(logado, caixa, db):
    await _transacao(logado, "100.00", "2026-11-15T12:00:00-03:00")
    await _transacao(logado, "200.00", "2026-12-15T12:00:00-03:00")

    await _rodar(db)
    await _rodar(db, datetime(2027, 1, 1, 12, 0, tzinfo=timezone.utc))

    assert await caixa.assuntos() == [
        "Seu resumo de novembro de 2026",
        "Seu resumo de dezembro de 2026",
    ]


@pytest.mark.parametrize(
    "agora, enviados",
    [
        (datetime(2026, 12, 1, 10, 59, tzinfo=timezone.utc), 0),
        (datetime(2026, 12, 3, 20, 0, tzinfo=timezone.utc), 1),
        (datetime(2026, 12, 4, 12, 0, tzinfo=timezone.utc), 0),
    ],
)
async def test_janela_de_envio(logado, caixa, db, agora, enviados):
    await _transacao(logado, "100.00", "2026-11-15T12:00:00-03:00")

    assert await _rodar(db, agora) == enviados


async def test_usa_o_fuso_do_usuario(logado, caixa, db):
    csrf = await obter_csrf(logado)
    await logado.patch("/auth/me", json={"fuso": "Asia/Tokyo"}, headers={"X-CSRF-Token": csrf})
    await _transacao(logado, "100.00", "2026-11-15T12:00:00+09:00")

    assert await _rodar(db, datetime(2026, 11, 30, 23, 0, tzinfo=timezone.utc)) == 1
    assert await caixa.assuntos() == ["Seu resumo de novembro de 2026"]


async def test_preferencia_desligada_nao_envia(logado, caixa, db):
    csrf = await obter_csrf(logado)
    await logado.patch("/auth/me", json={"resumo_mensal": False}, headers={"X-CSRF-Token": csrf})
    await _transacao(logado, "100.00", "2026-11-15T12:00:00-03:00")

    assert await _rodar(db) == 0


async def test_email_nao_verificado_nao_recebe(client, caixa, db):
    await cadastrar(client)
    await login(client)
    await _transacao(client, "100.00", "2026-11-15T12:00:00-03:00")
    await caixa.esvaziar()

    assert await _rodar(db) == 0
    assert await caixa.recebidos() == []


async def test_falha_no_envio_nao_reenvia(logado, caixa, db):
    await _transacao(logado, "100.00", "2026-11-15T12:00:00-03:00")
    caixa.falhar = True

    assert await _rodar(db) == 0

    caixa.falhar = False
    assert await _rodar(db) == 0


async def test_falha_nos_lembretes_nao_impede_o_resumo(monkeypatch):
    import utils.lembretes
    from utils.config import settings

    resumo_chamado = asyncio.Event()

    async def lembretes_quebrados(db, agora):
        raise RuntimeError("falha nos lembretes")

    async def resumos_falsos(db, agora):
        resumo_chamado.set()
        return 0

    monkeypatch.setattr(utils.lembretes, "enviar_lembretes", lembretes_quebrados)
    monkeypatch.setattr(utils.lembretes, "enviar_resumos", resumos_falsos)
    monkeypatch.setattr(settings, "LEMBRETES_INTERVALO_MIN", 0)

    tarefa = asyncio.create_task(utils.lembretes.executar_lembretes_periodicos())
    await asyncio.wait_for(resumo_chamado.wait(), timeout=5)
    tarefa.cancel()

    with pytest.raises(asyncio.CancelledError):
        await tarefa
