"""Create ids table

Revision ID: cc5236b5d791
Revises: 4dab622e073e
Create Date: 2025-09-20 21:13:56.115409

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc5236b5d791"
down_revision: Union[str, Sequence[str], None] = "4dab622e073e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ids",
        sa.Column("id", sa.VARCHAR, primary_key=True),
        sa.Column("ips", sa.ARRAY(sa.VARCHAR), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ids")
