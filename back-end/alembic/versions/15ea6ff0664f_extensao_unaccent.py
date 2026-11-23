"""extensao unaccent

Revision ID: 15ea6ff0664f
Revises: fe62f8078932
Create Date: 2026-11-23 01:23:26.464544

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15ea6ff0664f'
down_revision: Union[str, Sequence[str], None] = 'fe62f8078932'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS unaccent")
