"""add_payload_size_columns

Revision ID: a1b2c3d4e5f6
Revises: d483646e26ae
Create Date: 2025-12-30 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "d483646e26ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add request_size_bytes and response_size_bytes columns to tool_executions."""
    op.add_column(
        "tool_executions",
        sa.Column("request_size_bytes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tool_executions",
        sa.Column("response_size_bytes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Remove request_size_bytes and response_size_bytes columns from tool_executions."""
    op.drop_column("tool_executions", "response_size_bytes")
    op.drop_column("tool_executions", "request_size_bytes")
