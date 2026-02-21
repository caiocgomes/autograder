"""Add non-code grading support

Revision ID: a1b2c3d4e5f6
Revises: 031a92ead68d
Create Date: 2026-02-15

NOTE: All changes originally intended by this migration (content_hash rename,
file_path/file_name/file_size/content_type columns on submissions,
rubric_dimensions and rubric_scores tables) were absorbed into 031a92ead68d
(full_schema_with_course_orchestrator) when that migration was regenerated.
This migration is intentionally a no-op to preserve the revision chain
integrity without re-applying duplicate DDL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '031a92ead68d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
