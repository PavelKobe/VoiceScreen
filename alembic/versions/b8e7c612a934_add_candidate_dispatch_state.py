"""add dispatch state to candidates

Revision ID: b8e7c612a934
Revises: a7d5b1c46e23
Create Date: 2026-04-27 22:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'b8e7c612a934'
down_revision: Union[str, None] = 'a7d5b1c46e23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'candidates',
        sa.Column('attempts_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'candidates',
        sa.Column('next_attempt_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('candidates', 'next_attempt_at')
    op.drop_column('candidates', 'attempts_count')
