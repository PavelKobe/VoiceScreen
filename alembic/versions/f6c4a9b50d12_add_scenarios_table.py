"""add scenarios table

Revision ID: f6c4a9b50d12
Revises: e5b3c8d09f01
Create Date: 2026-04-26 18:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'f6c4a9b50d12'
down_revision: Union[str, None] = 'e5b3c8d09f01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'scenarios',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column(
            'agent_role',
            sa.String(length=255),
            nullable=False,
            server_default='HR-помощник',
        ),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('vacancy_title', sa.String(length=255), nullable=False),
        sa.Column('questions', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_scenarios_client_id', 'scenarios', ['client_id'])
    op.create_unique_constraint(
        'uq_scenarios_client_slug', 'scenarios', ['client_id', 'slug']
    )


def downgrade() -> None:
    op.drop_constraint('uq_scenarios_client_slug', 'scenarios', type_='unique')
    op.drop_index('ix_scenarios_client_id', table_name='scenarios')
    op.drop_table('scenarios')
