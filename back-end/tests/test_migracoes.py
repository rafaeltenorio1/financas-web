from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parent.parent


def test_models_e_migracoes_em_sincronia():
    """Equivale a `alembic check`: falha se algum model mudou sem migração
    (ou se um model novo não foi importado em models/__init__.py)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(RAIZ_BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    command.check(cfg)
