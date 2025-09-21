"""Create boards table

Revision ID: 91c0a060321e
Revises: cc5236b5d791
Create Date: 2025-09-21 09:19:44.357335

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "91c0a060321e"
down_revision: Union[str, Sequence[str], None] = "cc5236b5d791"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "boards",
        sa.Column("id", sa.VARCHAR, primary_key=True),
        sa.Column("name", sa.VARCHAR, nullable=False),
        sa.Column("description", sa.String, nullable=False, server_default=""),
        sa.Column(
            "anon_name",
            sa.VARCHAR,
            nullable=False,
            server_default="名無しさん@14ちゃんねる！",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("boards")
