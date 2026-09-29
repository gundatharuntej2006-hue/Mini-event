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

_STATUS = sa.Enum(
    "PENDING", "RECOVERED", "PURCHASED", "MISSING",
    name="fragment_status_enum",
    create_constraint=False,
)


def upgrade() -> None:
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
