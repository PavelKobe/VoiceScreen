"""add dispatch_paused column to vacancies

Revision ID: c9f8d023b145
Revises: b8e7c612a934
Create Date: 2026-04-30 18:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'c9f8d023b145'
down_revision: Union[str, None] = 'b8e7c612a934'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'vacancies',
        sa.Column(
            'dispatch_paused',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column('vacancies', 'dispatch_paused')
