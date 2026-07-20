"""add_sms_send_logs

Revision ID: f5a7c9e1b3d0
Revises: e3f1a2b4c6d8
Create Date: 2026-07-20 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5a7c9e1b3d0'
down_revision: Union[str, None] = 'e3f1a2b4c6d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sms_send_logs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sms_send_logs_phone'), 'sms_send_logs', ['phone'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sms_send_logs_phone'), table_name='sms_send_logs')
    op.drop_table('sms_send_logs')
