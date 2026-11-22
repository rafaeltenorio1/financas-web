import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address

import pytest
from sqlalchemy import func, select

from apoio import cadastrar


@pytest.fixture
async def id_usuario(client, db):
    from models.usuario import Usuario

    await cadastrar(client)
    return await db.scalar(select(Usuario.id_usuario))


async def _criar_sessao(db, id_usuario, criada_em, ultimo_acesso_em, expira_em):
    from models.sessao import Sessao

    sessao = Sessao(
        id_usuario=id_usuario,
        token_hash=uuid.uuid4().hex,
        criada_em=criada_em,
        ultimo_acesso_em=ultimo_acesso_em,
        expira_em=expira_em,
    )
    db.add(sessao)
    await db.commit()
    return sessao.id_sessao


async def _criar_tentativa(db, ocorrida_em):
    from models.log_tentativa import LogTentativa

    tentativa = LogTentativa(
        email_tentativa="ana@example.com",
        ip=ip_address("10.0.0.1"),
        ocorrida_em=ocorrida_em,
        sucesso=False,
    )
    db.add(tentativa)
    await db.commit()
    return tentativa.id_log_tentativa


async def _ids_sessoes(db):
    from models.sessao import Sessao

    db.expire_all()
    return set(await db.scalars(select(Sessao.id_sessao)))


async def _ids_tentativas(db):
    from models.log_tentativa import LogTentativa

    db.expire_all()
    return set(await db.scalars(select(LogTentativa.id_log_tentativa)))


async def test_apaga_sessao_expirada_e_inativa_e_mantem_valida(id_usuario, db):
    from utils.config import settings
    from utils.limpeza import limpar_dados_vencidos

    agora = datetime.now(timezone.utc)
    inatividade = timedelta(minutes=settings.SESSAO_INATIVIDADE_MIN)

    expirada = await _criar_sessao(
        db, id_usuario,
        criada_em=agora - timedelta(days=8),
        ultimo_acesso_em=agora - timedelta(minutes=1),
        expira_em=agora - timedelta(seconds=1),
    )
    inativa = await _criar_sessao(
        db, id_usuario,
        criada_em=agora - timedelta(hours=2),
        ultimo_acesso_em=agora - inatividade - timedelta(seconds=1),
        expira_em=agora + timedelta(days=6),
    )
    valida = await _criar_sessao(
        db, id_usuario,
        criada_em=agora - timedelta(hours=1),
        ultimo_acesso_em=agora - timedelta(minutes=5),
        expira_em=agora + timedelta(days=6),
    )

    sessoes, _ = await limpar_dados_vencidos(db, agora)

    assert sessoes == 2
    restantes = await _ids_sessoes(db)
    assert valida in restantes
    assert expirada not in restantes
    assert inativa not in restantes


async def test_limites_da_sessao_seguem_o_mesmo_criterio_da_autenticacao(id_usuario, db):
    from utils.config import settings
    from utils.limpeza import limpar_dados_vencidos

    agora = datetime.now(timezone.utc)
    inatividade = timedelta(minutes=settings.SESSAO_INATIVIDADE_MIN)

    expira_agora = await _criar_sessao(
        db, id_usuario,
        criada_em=agora - timedelta(days=7),
        ultimo_acesso_em=agora - timedelta(minutes=1),
        expira_em=agora,
    )
    no_limite_da_inatividade = await _criar_sessao(
        db, id_usuario,
        criada_em=agora - timedelta(hours=2),
        ultimo_acesso_em=agora - inatividade,
        expira_em=agora + timedelta(days=6),
    )

    await limpar_dados_vencidos(db, agora)

    restantes = await _ids_sessoes(db)
    assert expira_agora not in restantes
    assert no_limite_da_inatividade in restantes


async def test_apaga_so_tentativas_mais_antigas_que_a_retencao(db):
    from utils.config import settings
    from utils.limpeza import limpar_dados_vencidos

    agora = datetime.now(timezone.utc)
    retencao = timedelta(days=settings.TENTATIVAS_RETENCAO_DIAS)

    antiga = await _criar_tentativa(db, agora - retencao - timedelta(seconds=1))
    no_limite = await _criar_tentativa(db, agora - retencao)
    recente = await _criar_tentativa(db, agora - timedelta(minutes=1))

    _, tentativas = await limpar_dados_vencidos(db, agora)

    assert tentativas == 1
    restantes = await _ids_tentativas(db)
    assert antiga not in restantes
    assert no_limite in restantes
    assert recente in restantes


async def test_nao_apaga_usuario_nem_transacoes(logado, db):
    from models.sessao import Sessao
    from models.transacao import Transacao
    from models.usuario import Usuario
    from utils.limpeza import limpar_dados_vencidos

    from apoio import obter_csrf

    csrf = await obter_csrf(logado)
    resposta = await logado.post(
        "/transacoes",
        json={
            "valor": "50.00",
            "tipo": "despesa",
            "data_hora": datetime.now(timezone.utc).isoformat(),
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 201, resposta.text

    await limpar_dados_vencidos(db, datetime.now(timezone.utc) + timedelta(days=8))

    db.expire_all()
    assert await db.scalar(select(func.count()).select_from(Sessao)) == 0
    assert await db.scalar(select(func.count()).select_from(Usuario)) == 1
    assert await db.scalar(select(func.count()).select_from(Transacao)) == 1


async def test_laco_continua_depois_de_uma_falha(monkeypatch):
    import utils.limpeza
    from utils.config import settings

    chamadas = 0
    segunda_chamada = asyncio.Event()

    async def limpeza_falsa(db, agora):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            raise RuntimeError("banco fora do ar")
        segunda_chamada.set()
        return 0, 0

    monkeypatch.setattr(utils.limpeza, "limpar_dados_vencidos", limpeza_falsa)
    monkeypatch.setattr(settings, "LIMPEZA_INTERVALO_MIN", 0)

    tarefa = asyncio.create_task(utils.limpeza.executar_limpeza_periodica())
    await asyncio.wait_for(segunda_chamada.wait(), timeout=5)
    tarefa.cancel()

    with pytest.raises(asyncio.CancelledError):
        await tarefa
    assert chamadas >= 2
