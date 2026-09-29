"""ODDyssey Section 5: second organiser signature on Black Market purchases

"Every transaction requires two organiser signatures." Only the acting
organiser was recorded, so the paper control had no counterpart in the ledger.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "black_market_purchases"
COLUMN = "countersigned_by"


def _columns():
    inspector = sa.inspect(op.get_bind())
    if TABLE not in inspector.get_table_names():
        return None
    return {c["name"] for c in inspector.get_columns(TABLE)}


def upgrade() -> None:
    present = _columns()
    if present is None or COLUMN in present:
        return
    with op.batch_alter_table(TABLE) as batch_op:
        batch_op.add_column(sa.Column(COLUMN, sa.String(length=255), nullable=True))


def downgrade() -> None:
    present = _columns()
    if present is None or COLUMN not in present:
        return
    with op.batch_alter_table(TABLE) as batch_op:
        batch_op.drop_column(COLUMN)
