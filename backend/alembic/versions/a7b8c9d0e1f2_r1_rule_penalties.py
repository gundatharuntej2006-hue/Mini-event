"""ODDyssey Section 4: Round 1 rule penalties

Round 1 is ranked on "time spent at gates + hint penalties + rule penalties",
but only the hint penalty had anywhere to live. These columns hold the three
rule violations a gate marshal logs, plus the time they add.

round1_timings is not created by any migration - it is one of the tables
Base.metadata.create_all builds at startup - so this revision only widens the
table where it already exists. On a database that has never run the app, the
table is created later with these columns already on it, which is why the
upgrade is written to be a no-op in that case rather than to fail.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "round1_timings"
_COLUMNS = (
    "phone_use_count",
    "separation_count",
    "clue_damage_count",
    "rule_penalty_seconds",
)


def _existing_columns() -> set:
    inspector = sa.inspect(op.get_bind())
    if TABLE not in inspector.get_table_names():
        return None
    return {c["name"] for c in inspector.get_columns(TABLE)}


def upgrade() -> None:
    present = _existing_columns()
    if present is None:
        return

    missing = [name for name in _COLUMNS if name not in present]
    if not missing:
        return

    # batch_alter_table so this also runs on SQLite, which cannot ALTER a
    # column in place.
    with op.batch_alter_table(TABLE) as batch_op:
        for name in missing:
            batch_op.add_column(
                sa.Column(name, sa.Integer(), nullable=False, server_default="0")
            )


def downgrade() -> None:
    present = _existing_columns()
    if present is None:
        return

    drops = [name for name in reversed(_COLUMNS) if name in present]
    if not drops:
        return

    with op.batch_alter_table(TABLE) as batch_op:
        for name in drops:
            batch_op.drop_column(name)
