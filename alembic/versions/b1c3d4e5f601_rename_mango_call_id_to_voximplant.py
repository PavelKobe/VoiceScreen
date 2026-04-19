"""rename mango_call_id to voximplant_call_id

Revision ID: b1c3d4e5f601
Revises: a2a2e90a20ae
Create Date: 2026-04-19 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b1c3d4e5f601'
down_revision: Union[str, None] = 'a2a2e90a20ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('calls', 'mango_call_id', new_column_name='voximplant_call_id')


def downgrade() -> None:
    op.alter_column('calls', 'voximplant_call_id', new_column_name='mango_call_id')
