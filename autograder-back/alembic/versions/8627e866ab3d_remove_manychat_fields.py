"""remove manychat fields

Revision ID: 8627e866ab3d
Revises: 7af56f19e432
Create Date: 2026-02-21 00:22:31.040008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8627e866ab3d'
down_revision: Union[str, None] = '7af56f19e432'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove manychat_tag rules before altering the enum
    # DB stores enum names in uppercase (SQLAlchemy default for pg enum)
    op.execute("DELETE FROM product_access_rules WHERE rule_type = 'MANYCHAT_TAG'")

    # Remove manychat_subscriber_id column from users
    op.drop_column('users', 'manychat_subscriber_id')

    # Remove 'MANYCHAT_TAG' from the accessruletype enum in PostgreSQL
    # Alembic doesn't auto-generate enum value removals, so we do it manually
    op.execute("ALTER TYPE accessruletype RENAME TO accessruletype_old")
    op.execute("CREATE TYPE accessruletype AS ENUM ('DISCORD_ROLE', 'CLASS_ENROLLMENT')")
    op.execute("ALTER TABLE product_access_rules ALTER COLUMN rule_type TYPE accessruletype USING rule_type::text::accessruletype")
    op.execute("DROP TYPE accessruletype_old")


def downgrade() -> None:
    # Restore 'MANYCHAT_TAG' to the enum
    op.execute("ALTER TYPE accessruletype RENAME TO accessruletype_old")
    op.execute("CREATE TYPE accessruletype AS ENUM ('DISCORD_ROLE', 'CLASS_ENROLLMENT', 'MANYCHAT_TAG')")
    op.execute("ALTER TABLE product_access_rules ALTER COLUMN rule_type TYPE accessruletype USING rule_type::text::accessruletype")
    op.execute("DROP TYPE accessruletype_old")

    # Restore manychat_subscriber_id column
    op.add_column('users', sa.Column('manychat_subscriber_id', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
