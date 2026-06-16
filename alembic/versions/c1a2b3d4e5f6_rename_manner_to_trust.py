"""rename_manner_to_trust

Revision ID: c1a2b3d4e5f6
Revises: b91fe51169d6
Create Date: 2026-06-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, None] = "b91fe51169d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("user_profiles", "manner_score", new_column_name="trust_score")
    op.alter_column("user_profiles", "manner_grade", new_column_name="trust_grade")


def downgrade() -> None:
    op.alter_column("user_profiles", "trust_score", new_column_name="manner_score")
    op.alter_column("user_profiles", "trust_grade", new_column_name="manner_grade")
