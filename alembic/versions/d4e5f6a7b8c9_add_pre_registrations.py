"""add_pre_registrations

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a8b9
Create Date: 2026-10-28 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # genderenum 타입은 users 테이블 생성 때 이미 만들어져 있다 — 다시 만들지 않는다
    gender_enum = postgresql.ENUM("male", "female", name="genderenum", create_type=False)
    op.create_table(
        "pre_registrations",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=30), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("gender", gender_enum, nullable=False),
        sa.Column("birth_year", sa.Integer(), nullable=False),
        sa.Column("region", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=True),
        sa.Column("privacy_consent", sa.Boolean(), nullable=False),
        sa.Column(
            "marketing_consent",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone"),
    )


def downgrade() -> None:
    op.drop_table("pre_registrations")
