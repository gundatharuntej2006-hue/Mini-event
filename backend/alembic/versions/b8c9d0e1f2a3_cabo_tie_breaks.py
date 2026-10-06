"""ODDyssey Section 4: Cabo tie-breakers 4 and 5

The platform computed tie-breakers 1-3 from the scorecards and then stopped,
flagging anything still level as "unresolved" with no route to resolve it.
Round 2 cuts 24 squads to 12 and an unresolved tie blocks finalisation, so a
genuinely level tie across that boundary could stall the round. This table
holds the sudden-death result or the organiser draw that separates them.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "cabo_tie_break_resolutions"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if TABLE in inspector.get_table_names():
        return

    op.create_table(
        TABLE,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("team_id", sa.String(length=36), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("resolution_rank", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.String(length=255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", name="uq_cabo_tie_break_team"),
        sa.CheckConstraint(
            "method IN ('SUDDEN_DEATH', 'ORGANISER_DRAW')",
            name="ck_cabo_tie_break_method",
        ),
        sa.CheckConstraint("resolution_rank >= 1", name="ck_cabo_tie_break_rank"),
    )
    op.create_index(
        op.f("ix_cabo_tie_break_resolutions_team_id"), TABLE, ["team_id"], unique=False
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if TABLE not in inspector.get_table_names():
        return
    op.drop_index(op.f("ix_cabo_tie_break_resolutions_team_id"), table_name=TABLE)
    op.drop_table(TABLE)
