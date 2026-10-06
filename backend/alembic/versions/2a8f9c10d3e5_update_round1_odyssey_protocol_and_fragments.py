"""update_round1_odyssey_protocol_and_fragments

Revision ID: 2a8f9c10d3e5
Revises: 09381d687e36
Create Date: 2026-10-05 17:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a8f9c10d3e5'
down_revision: Union[str, None] = '09381d687e36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update round1_timings for the ODDyssey Protocol penalties and DQ
    with op.batch_alter_table('round1_timings') as batch_op:
        batch_op.add_column(sa.Column('phone_penalties_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('phone_penalty_seconds', sa.Integer(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('separation_penalties_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('separation_penalty_seconds', sa.Integer(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('clue_tampering_deduction', sa.Integer(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('is_disqualified', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('disqualification_reason', sa.String(length=255), nullable=True))

    # 2. Update final_code_records for 4-fragment code hunt and Gate 3 confirmation
    with op.batch_alter_table('final_code_records') as batch_op:
        batch_op.add_column(sa.Column('fragment_3_status', sa.String(length=50), nullable=False, server_default=sa.text("'PENDING'")))
        batch_op.add_column(sa.Column('fragment_3_value', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('fragment_3_discovered_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('fragment_4_status', sa.String(length=50), nullable=False, server_default=sa.text("'PENDING'")))
        batch_op.add_column(sa.Column('fragment_4_value', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('fragment_4_discovered_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('gate_3_confirmed', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('gate_3_confirmed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('gate_3_confirmed_by', sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('final_code_records') as batch_op:
        batch_op.drop_column('gate_3_confirmed_by')
        batch_op.drop_column('gate_3_confirmed_at')
        batch_op.drop_column('gate_3_confirmed')
        batch_op.drop_column('fragment_4_discovered_at')
        batch_op.drop_column('fragment_4_value')
        batch_op.drop_column('fragment_4_status')
        batch_op.drop_column('fragment_3_discovered_at')
        batch_op.drop_column('fragment_3_value')
        batch_op.drop_column('fragment_3_status')

    with op.batch_alter_table('round1_timings') as batch_op:
        batch_op.drop_column('disqualification_reason')
        batch_op.drop_column('is_disqualified')
        batch_op.drop_column('clue_tampering_deduction')
        batch_op.drop_column('separation_penalty_seconds')
        batch_op.drop_column('separation_penalties_count')
        batch_op.drop_column('phone_penalty_seconds')
        batch_op.drop_column('phone_penalties_count')
