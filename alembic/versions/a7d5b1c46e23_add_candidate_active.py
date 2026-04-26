"""add active column to candidates

Revision ID: a7d5b1c46e23
Revises: f6c4a9b50d12
Create Date: 2026-04-26 19:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'a7d5b1c46e23'
down_revision: Union[str, None] = 'f6c4a9b50d12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'candidates',
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column('candidates', 'active')
