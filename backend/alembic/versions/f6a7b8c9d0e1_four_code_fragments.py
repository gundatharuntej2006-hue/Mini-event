"""Hold four code fragments, not two

The ODDyssey plan, Section 2, sets the complete secret code as
ODD - 42 - ECHO - PRIME: four fragments, two hidden in each of the first two
rounds.

    ODD    Round 1, The Signal Scramble
    42     Round 1, The Route Riddle
    ECHO   Round 2, marked Cabo cards
    PRIME  Round 2, Prime Number Challenge

final_code_records held only fragment_1 and fragment_2, so a team could never
record more than half its code and the Round 4 gate could never be satisfied
under the current plan.

Revision ID: f6a7b8c9d0e1
Revises: 1d7dc59f4a11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "1d7dc59f4a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LABELS = ("PENDING", "RECOVERED", "PURCHASED", "MISSING")
_ENUM_NAME = "fragment_status_enum"


def _status_type():
    """
    The fragment-status type, reusing the one that already exists.

    1d7dc59f4a11 created final_code_records with fragment_1_status as an Enum,
    which on PostgreSQL also created the TYPE fragment_status_enum. Adding two
    more columns of that same type must NOT try to create it again — Postgres
    fails with "type already exists" — so the dialect-specific ENUM is asked
    for with create_type=False.

    SQLite has no enum types at all; it stores them as VARCHAR with an
    optional CHECK. That is exactly why this was invisible locally: every
    test and every migration rehearsal ran on SQLite, where re-declaring an
    enum is free, and the first Postgres this ever met was production.
    """
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects import postgresql

        return postgresql.ENUM(*_LABELS, name=_ENUM_NAME, create_type=False)
    return sa.Enum(*_LABELS, name=_ENUM_NAME, create_constraint=False)


def upgrade() -> None:
    _STATUS = _status_type()
    with op.batch_alter_table("final_code_records", schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            "fragment_3_status", _STATUS, nullable=False, server_default="PENDING"
        ))
        batch_op.add_column(sa.Column("fragment_3_value", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column(
            "fragment_3_discovered_at", sa.DateTime(timezone=True), nullable=True
        ))
        batch_op.add_column(sa.Column(
            "fragment_4_status", _STATUS, nullable=False, server_default="PENDING"
        ))
        batch_op.add_column(sa.Column("fragment_4_value", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column(
            "fragment_4_discovered_at", sa.DateTime(timezone=True), nullable=True
        ))


def downgrade() -> None:
    # Any team that had assembled a four-part code no longer holds a complete
    # one, so clear the verification rather than leave a gate open on a code
    # that can no longer exist.
    op.execute(
        "UPDATE final_code_records SET final_code_verified = 0, "
        "final_code_assembled = NULL, verified_at = NULL, verified_by = NULL"
    )
    with op.batch_alter_table("final_code_records", schema=None) as batch_op:
        batch_op.drop_column("fragment_4_discovered_at")
        batch_op.drop_column("fragment_4_value")
        batch_op.drop_column("fragment_4_status")
        batch_op.drop_column("fragment_3_discovered_at")
        batch_op.drop_column("fragment_3_value")
        batch_op.drop_column("fragment_3_status")
