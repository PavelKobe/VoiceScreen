"""add api_key to clients

Revision ID: d4a2f1c3e802
Revises: c3f1a0b2d701
Create Date: 2026-04-25 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'd4a2f1c3e802'
down_revision: Union[str, None] = 'c3f1a0b2d701'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clients', sa.Column('api_key', sa.String(length=64), nullable=True))
    op.create_unique_constraint('uq_clients_api_key', 'clients', ['api_key'])
    op.create_index('ix_clients_api_key', 'clients', ['api_key'])


def downgrade() -> None:
    op.drop_index('ix_clients_api_key', table_name='clients')
    op.drop_constraint('uq_clients_api_key', 'clients', type_='unique')
    op.drop_column('clients', 'api_key')
