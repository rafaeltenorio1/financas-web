"""remove categorias genericas antigas

Revision ID: fb38c83c2cf3
Revises: 85ba15b30ff1
Create Date: 2026-11-10 04:30:36.542503

"""
import uuid

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb38c83c2cf3'
down_revision: Union[str, Sequence[str], None] = '85ba15b30ff1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ANTIGAS = ["Alimentação", "Moradia", "Transporte"]


def upgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM categoria WHERE id_usuario IS NULL AND nome = ANY(:nomes)"
        ).bindparams(nomes=ANTIGAS)
    )


def downgrade() -> None:
    for nome in ANTIGAS:
        op.execute(
            sa.text(
                "INSERT INTO categoria (id_categoria, nome, tipo_padrao) "
                "VALUES (:id, :nome, 'DESPESA') ON CONFLICT DO NOTHING"
            ).bindparams(id=uuid.uuid4(), nome=nome)
        )