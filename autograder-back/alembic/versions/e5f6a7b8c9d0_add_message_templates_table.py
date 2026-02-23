"""Add message_templates table

Revision ID: e5f6a7b8c9d0
Revises: d42982779265
Create Date: 2026-02-22 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd42982779265'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('message_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.Enum('ONBOARDING', 'WELCOME', 'WELCOME_BACK', 'CHURN', name='templateeventtype'), unique=True, nullable=False),
    sa.Column('template_text', sa.Text(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_message_templates_id'), 'message_templates', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_message_templates_id'), table_name='message_templates')
    op.drop_table('message_templates')
    sa.Enum('ONBOARDING', 'WELCOME', 'WELCOME_BACK', 'CHURN', name='templateeventtype').drop(op.get_bind(), checkfirst=True)
