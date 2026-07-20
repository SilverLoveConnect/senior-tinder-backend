"""add_sms_verification_attempt_count

Revision ID: e3f1a2b4c6d8
Revises: 1794dc2b08fc
Create Date: 2026-07-20 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3f1a2b4c6d8'
down_revision: Union[str, None] = '1794dc2b08fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sms_verifications',
        sa.Column('attempt_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    )


def downgrade() -> None:
    op.drop_column('sms_verifications', 'attempt_count')
