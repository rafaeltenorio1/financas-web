from datetime import datetime, timedelta, timezone

import pyotp
from sqlalchemy import select, update

from apoio import SENHA_PADRAO, cadastrar, criar_cliente, login, obter_csrf


async def _unica_sessao(db):
    from models.sessao import Sessao

    db.expire_all()
    return (await db.scalars(select(Sessao))).all()


async def _envelhecer_sessao(db, criada_ha: timedelta, sem_uso_ha: timedelta):
    from models.sessao import Sessao

    agora = datetime.now(timezone.utc)
    await db.execute(
        update(Sessao).values(criada_em=agora - criada_ha, ultimo_acesso_em=agora - sem_uso_ha)
    )
    await db.commit()


async def test_sem_lembrar_cookie_morre_ao_fechar_o_navegador(client, db):
    from utils.config import settings

    await cadastrar(client)
    resposta = await login(client)

    assert resposta.status_code == 200
    set_cookie = resposta.headers["set-cookie"].lower()
    assert "max-age" not in set_cookie
    assert "expires" not in set_cookie

    [sessao] = await _unica_sessao(db)
    assert sessao.lembrar is False
    duracao = sessao.expira_em - sessao.criada_em
    assert abs(duracao - timedelta(days=settings.SESSAO_DURACAO_DIAS)) < timedelta(minutes=1)


async def test_com_lembrar_cookie_persiste_pela_duracao_maxima(client, db):
    from utils.config import settings

    await cadastrar(client)
    resposta = await login(client, lembrar=True)

    assert resposta.status_code == 200
    segundos = settings.SESSAO_LEMBRAR_DURACAO_DIAS * 86400
    assert f"max-age={segundos}" in resposta.headers["set-cookie"].lower()

    [sessao] = await _unica_sessao(db)
    assert sessao.lembrar is True
    duracao = sessao.expira_em - sessao.criada_em
    assert abs(duracao - timedelta(days=settings.SESSAO_LEMBRAR_DURACAO_DIAS)) < timedelta(minutes=1)


async def test_sessao_lembrada_sobrevive_a_horas_sem_uso(client, db):
    await cadastrar(client)
    await login(client, lembrar=True)
    await _envelhecer_sessao(db, criada_ha=timedelta(days=3), sem_uso_ha=timedelta(hours=2))

    assert (await client.get("/auth/me")).status_code == 200


async def test_sessao_comum_continua_expirando_por_inatividade(client, db):
    from utils.config import settings

    await cadastrar(client)
    await login(client)
    await _envelhecer_sessao(
        db,
        criada_ha=timedelta(hours=2),
        sem_uso_ha=timedelta(minutes=settings.SESSAO_INATIVIDADE_MIN + 1),
    )

    assert (await client.get("/auth/me")).status_code == 401


async def test_sessao_lembrada_expira_depois_de_dias_sem_uso(client, db):
    from utils.config import settings

    await cadastrar(client)
    await login(client, lembrar=True)
    await _envelhecer_sessao(
        db,
        criada_ha=timedelta(days=settings.SESSAO_LEMBRAR_INATIVIDADE_DIAS + 5),
        sem_uso_ha=timedelta(days=settings.SESSAO_LEMBRAR_INATIVIDADE_DIAS, minutes=1),
    )

    assert (await client.get("/auth/me")).status_code == 401
    assert await _unica_sessao(db) == []


async def test_sessao_lembrada_respeita_a_duracao_maxima(client, db):
    from models.sessao import Sessao

    await cadastrar(client)
    await login(client, lembrar=True)

    agora = datetime.now(timezone.utc)
    await db.execute(
        update(Sessao).values(
            criada_em=agora - timedelta(days=91),
            ultimo_acesso_em=agora - timedelta(minutes=1),
            expira_em=agora - timedelta(seconds=1),
        )
    )
    await db.commit()

    assert (await client.get("/auth/me")).status_code == 401


async def test_lembrar_atravessa_o_fluxo_do_2fa(logado, db):
    from models.desafio_2fa import Desafio2FA
    from models.usuario import Usuario
    from utils.config import settings

    csrf = await obter_csrf(logado)
    segredo = (await logado.post("/auth/2fa/iniciar", headers={"X-CSRF-Token": csrf})).json()["segredo"]
    resposta = await logado.post(
        "/auth/2fa/ativar",
        json={"senha": SENHA_PADRAO, "codigo": pyotp.TOTP(segredo).now()},
        headers={"X-CSRF-Token": csrf},
    )
    assert resposta.status_code == 200, resposta.text
    await db.execute(update(Usuario).values(totp_ultimo_passo=None))
    await db.commit()

    async with criar_cliente() as navegador:
        resposta = await login(navegador, lembrar=True)
        assert resposta.json() == {"requer_2fa": True}
        desafio = await db.scalar(select(Desafio2FA))
        assert desafio.lembrar is True

        resposta = await navegador.post("/auth/login/2fa", json={"codigo": pyotp.TOTP(segredo).now()})

        assert resposta.status_code == 200, resposta.text
        segundos = settings.SESSAO_LEMBRAR_DURACAO_DIAS * 86400
        assert f"max-age={segundos}" in resposta.headers["set-cookie"].lower()

    from models.sessao import Sessao

    db.expire_all()
    assert (await db.scalars(select(Desafio2FA))).all() == []
    assert set(await db.scalars(select(Sessao.lembrar))) == {False, True}
