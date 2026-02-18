"""Add non-code grading support

Revision ID: a1b2c3d4e5f6
Revises: 869b0b496579
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '869b0b496579'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums
    submission_type_enum = sa.Enum('code', 'file_upload', name='submissiontype')
    grading_mode_enum = sa.Enum('test_first', 'llm_first', name='gradingmode')
    submission_type_enum.create(op.get_bind(), checkfirst=True)
    grading_mode_enum.create(op.get_bind(), checkfirst=True)

    # Add new columns to exercises
    op.add_column('exercises', sa.Column(
        'submission_type', submission_type_enum,
        nullable=False, server_default='code'
    ))
    op.add_column('exercises', sa.Column(
        'grading_mode', grading_mode_enum,
        nullable=False, server_default='test_first'
    ))

    # Alter submissions: make code nullable
    op.alter_column('submissions', 'code', existing_type=sa.Text(), nullable=True)

    # Rename code_hash to content_hash
    op.alter_column('submissions', 'code_hash', new_column_name='content_hash')

    # Add file metadata columns to submissions
    op.add_column('submissions', sa.Column('file_path', sa.String(500), nullable=True))
    op.add_column('submissions', sa.Column('file_name', sa.String(255), nullable=True))
    op.add_column('submissions', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('submissions', sa.Column('content_type', sa.String(100), nullable=True))

    # Rename code_hash to content_hash in llm_evaluations
    op.alter_column('llm_evaluations', 'code_hash', new_column_name='content_hash')

    # Create rubric_dimensions table
    op.create_table(
        'rubric_dimensions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('exercise_id', sa.Integer(), sa.ForeignKey('exercises.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
    )

    # Create rubric_scores table
    op.create_table(
        'rubric_scores',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('submission_id', sa.Integer(), sa.ForeignKey('submissions.id'), nullable=False, index=True),
        sa.Column('dimension_id', sa.Integer(), sa.ForeignKey('rubric_dimensions.id'), nullable=False, index=True),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.UniqueConstraint('submission_id', 'dimension_id', name='uq_rubric_score_submission_dimension'),
    )


def downgrade() -> None:
    op.drop_table('rubric_scores')
    op.drop_table('rubric_dimensions')

    # Remove file metadata columns from submissions
    op.drop_column('submissions', 'content_type')
    op.drop_column('submissions', 'file_size')
    op.drop_column('submissions', 'file_name')
    op.drop_column('submissions', 'file_path')

    # Rename content_hash back to code_hash
    op.alter_column('llm_evaluations', 'content_hash', new_column_name='code_hash')
    op.alter_column('submissions', 'content_hash', new_column_name='code_hash')

    # Make code non-nullable again
    op.alter_column('submissions', 'code', existing_type=sa.Text(), nullable=False)

    # Remove new columns from exercises
    op.drop_column('exercises', 'grading_mode')
    op.drop_column('exercises', 'submission_type')

    # Drop enums
    sa.Enum(name='gradingmode').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='submissiontype').drop(op.get_bind(), checkfirst=True)
