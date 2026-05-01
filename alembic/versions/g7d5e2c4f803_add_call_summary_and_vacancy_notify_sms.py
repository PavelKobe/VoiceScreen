"""add call summary, vacancy notify_emails/notify_on, vacancy sms_* fields

Revision ID: g7d5e2c4f803
Revises: f6c4a9b50d12
Create Date: 2026-05-01 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'g7d5e2c4f803'
down_revision: Union[str, None] = 'f6c4a9b50d12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Call: краткое резюме от LLM (генерится в score_call вместе с answers/score)
    op.add_column('calls', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('calls', sa.Column('sms_sent_at', sa.DateTime(), nullable=True))

    # Vacancy: уведомления HR по email
    op.add_column('vacancies', sa.Column('notify_emails', sa.JSON(), nullable=True))
    op.add_column(
        'vacancies',
        sa.Column(
            'notify_on',
            sa.String(length=20),
            nullable=False,
            server_default='pass_review',
        ),
    )

    # Vacancy: SMS перед звонком
    op.add_column(
        'vacancies',
        sa.Column(
            'sms_enabled',
            sa.Boolean(),
            nullable=False,
            server_default='false',
        ),
    )
    op.add_column('vacancies', sa.Column('sms_template', sa.Text(), nullable=True))
    op.add_column(
        'vacancies',
        sa.Column(
            'sms_lead_minutes',
            sa.Integer(),
            nullable=False,
            server_default='15',
        ),
    )


def downgrade() -> None:
    op.drop_column('vacancies', 'sms_lead_minutes')
    op.drop_column('vacancies', 'sms_template')
    op.drop_column('vacancies', 'sms_enabled')
    op.drop_column('vacancies', 'notify_on')
    op.drop_column('vacancies', 'notify_emails')
    op.drop_column('calls', 'sms_sent_at')
    op.drop_column('calls', 'summary')
