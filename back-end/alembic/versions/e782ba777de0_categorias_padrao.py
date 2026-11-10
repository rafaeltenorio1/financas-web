"""categorias padrao

Revision ID: e782ba777de0
Revises: edd3dc74a004
Create Date: 2026-11-10 02:13:26.200441

"""
import uuid

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

CATEGORIAS = ["Alimentação", "Aluguel", "Transporte", "Salário"]

# revision identifiers, used by Alembic.
revision: str = 'e782ba777de0'
down_revision: Union[str, Sequence[str], None] = 'edd3dc74a004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    categoria = sa.table(
        "categoria",
        sa.column("id_categoria", sa.Uuid),
        sa.column("nome", sa.String),
    )
    op.bulk_insert(
        categoria,
        [{"id_categoria": uuid.uuid4(), "nome": nome} for nome in CATEGORIAS],
    )


def downgrade() -> None:
    op.execute("DELETE FROM categoria WHERE id_usuario IS NULL")
