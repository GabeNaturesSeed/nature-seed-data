"""add keywords to topics

Revision ID: a159c3c3cf1e
Revises: eea92202b43b
Create Date: 2026-04-24 15:07:18.105190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a159c3c3cf1e'
down_revision: Union[str, Sequence[str], None] = 'eea92202b43b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('topics', sa.Column('keywords', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('topics', 'keywords')
