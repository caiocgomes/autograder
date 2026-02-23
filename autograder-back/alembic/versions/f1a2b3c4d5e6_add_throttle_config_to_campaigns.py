"""Add throttle config to message_campaigns

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-02-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('message_campaigns', sa.Column('throttle_min_seconds', sa.Float(), nullable=True, server_default='15.0'))
    op.add_column('message_campaigns', sa.Column('throttle_max_seconds', sa.Float(), nullable=True, server_default='25.0'))


def downgrade() -> None:
    op.drop_column('message_campaigns', 'throttle_max_seconds')
    op.drop_column('message_campaigns', 'throttle_min_seconds')
