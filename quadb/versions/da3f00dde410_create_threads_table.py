"""Create threads table

Revision ID: da3f00dde410
Revises:
Create Date: 2025-09-20 12:11:41.757944

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "da3f00dde410"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "threads",
        sa.Column("id", sa.VARCHAR, primary_key=True),
        sa.Column("title", sa.VARCHAR, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "sort_key",
            sa.Integer,
            nullable=False,
        ),
        sa.Column("owner_id", sa.VARCHAR, nullable=False),
        sa.Column("owner_shown_id", sa.VARCHAR, nullable=False),
        sa.Column("host", sa.VARCHAR, nullable=False),
        sa.Column("attributes", sa.JSON(True), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("threads")
