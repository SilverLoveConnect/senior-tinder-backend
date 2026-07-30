"""add_review_status_to_user_photos

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-07-30 00:00:01.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a8"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

photo_review_status_enum = sa.Enum(
    "pending", "approved", "rejected", name="photoreviewstatusenum"
)


def upgrade() -> None:
    photo_review_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "user_photos",
        sa.Column(
            "review_status",
            photo_review_status_enum,
            server_default="pending",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("user_photos", "review_status")
    photo_review_status_enum.drop(op.get_bind(), checkfirst=True)
