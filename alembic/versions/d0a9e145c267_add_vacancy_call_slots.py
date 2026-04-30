"""add call_slots column to vacancies

Revision ID: d0a9e145c267
Revises: c9f8d023b145
Create Date: 2026-04-30 21:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'd0a9e145c267'
down_revision: Union[str, None] = 'c9f8d023b145'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'vacancies',
        sa.Column('call_slots', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('vacancies', 'call_slots')
