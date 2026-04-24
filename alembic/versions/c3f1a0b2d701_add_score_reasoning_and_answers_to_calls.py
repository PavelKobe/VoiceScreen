"""add score_reasoning and answers to calls

Revision ID: c3f1a0b2d701
Revises: b1c3d4e5f601
Create Date: 2026-04-24 13:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'c3f1a0b2d701'
down_revision: Union[str, None] = 'b1c3d4e5f601'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('calls', sa.Column('score_reasoning', sa.Text(), nullable=True))
    op.add_column('calls', sa.Column('answers', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('calls', 'answers')
    op.drop_column('calls', 'score_reasoning')
