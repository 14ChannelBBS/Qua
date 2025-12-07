"""Create responses table

Revision ID: 4dab622e073e
Revises: da3f00dde410
Create Date: 2025-09-20 19:36:53.578607

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4dab622e073e"
down_revision: Union[str, Sequence[str], None] = "da3f00dde410"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "responses",
        sa.Column("id", sa.VARCHAR, primary_key=True),
        sa.Column("parent_id", sa.VARCHAR, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("author_id", sa.VARCHAR, nullable=False),
        sa.Column("shown_id", sa.VARCHAR, nullable=False),
        sa.Column("host", sa.VARCHAR, nullable=False),
        sa.Column("name", sa.VARCHAR, nullable=True),
        sa.Column("content", sa.VARCHAR, nullable=True),
        sa.Column("reactions", sa.JSON(True), nullable=False, server_default="[]"),
        sa.Column("attributes", sa.JSON(True), nullable=False, server_default="{}"),
        sa.Column("deleted", sa.BOOLEAN, nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("responses")
