"""add users table

Revision ID: e5b3c8d09f01
Revises: d4a2f1c3e802
Create Date: 2026-04-26 13:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'e5b3c8d09f01'
down_revision: Union[str, None] = 'd4a2f1c3e802'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=30), nullable=False, server_default='client_admin'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_client_id', 'users', ['client_id'])


def downgrade() -> None:
    op.drop_index('ix_users_client_id', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_table('users')
