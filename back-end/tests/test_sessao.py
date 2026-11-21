from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update


async def _sessao_unica(db):
    from models.sessao import Sessao

    db.expire_all()
    return (await db.scalars(select(Sessao))).all()


async def test_sessao_expirada_e_recusada_e_apagada(logado, db):
    from models.sessao import Sessao

    agora = datetime.now(timezone.utc)
    await db.execute(
        update(Sessao).values(
            criada_em=agora - timedelta(days=8),
            ultimo_acesso_em=agora - timedelta(minutes=1),
            expira_em=agora - timedelta(seconds=1),
        )
    )
    await db.commit()

    assert (await logado.get("/auth/me")).status_code == 401
    assert await _sessao_unica(db) == []


async def test_sessao_inativa_e_recusada_e_apagada(logado, db):
    from models.sessao import Sessao
    from utils.config import settings

    agora = datetime.now(timezone.utc)
    await db.execute(
        update(Sessao).values(
            criada_em=agora - timedelta(hours=2),
            ultimo_acesso_em=agora - timedelta(minutes=settings.SESSAO_INATIVIDADE_MIN + 1),
        )
    )
    await db.commit()

    assert (await logado.get("/auth/me")).status_code == 401
    assert await _sessao_unica(db) == []


async def test_uso_renova_ultimo_acesso(logado, db):
    from models.sessao import Sessao

    agora = datetime.now(timezone.utc)
    antigo = agora - timedelta(minutes=10)
    await db.execute(
        update(Sessao).values(criada_em=agora - timedelta(hours=1), ultimo_acesso_em=antigo)
    )
    await db.commit()

    assert (await logado.get("/auth/me")).status_code == 200

    [sessao] = await _sessao_unica(db)
    assert sessao.ultimo_acesso_em > antigo + timedelta(minutes=5)
