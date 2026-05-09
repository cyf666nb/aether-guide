"""add landmark summary and admin password_hash

Revision ID: 0002_auth_and_summary
Revises: 369167cfdb09
Create Date: 2026-05-09 22:59:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_auth_and_summary"
down_revision: str | None = "369167cfdb09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Task 4 — align landmarks.summary with LandmarkDTO.
    op.add_column(
        "landmarks",
        sa.Column(
            "summary",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    # Task 5 — admin auth: bcrypt hash column.
    op.add_column(
        "admins",
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("admins", "password_hash")
    op.drop_column("landmarks", "summary")
