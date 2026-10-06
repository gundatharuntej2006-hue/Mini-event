"""add_r2_cabo_echo_prime_verifications

Revision ID: 4c1a8e23b9d0
Revises: 3b9e8f12a4c6
Create Date: 2026-10-05 18:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c1a8e23b9d0'
down_revision = '3b9e8f12a4c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('final_code_records')]

    with op.batch_alter_table('final_code_records') as batch_op:
        if 'echo_e_verified' not in cols:
            batch_op.add_column(sa.Column('echo_e_verified', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        if 'echo_e_verified_at' not in cols:
            batch_op.add_column(sa.Column('echo_e_verified_at', sa.DateTime(), nullable=True))
        if 'echo_c_verified' not in cols:
            batch_op.add_column(sa.Column('echo_c_verified', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        if 'echo_c_verified_at' not in cols:
            batch_op.add_column(sa.Column('echo_c_verified_at', sa.DateTime(), nullable=True))
        if 'echo_ho_verified' not in cols:
            batch_op.add_column(sa.Column('echo_ho_verified', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        if 'echo_ho_verified_at' not in cols:
            batch_op.add_column(sa.Column('echo_ho_verified_at', sa.DateTime(), nullable=True))
        if 'prime_sequence_verified' not in cols:
            batch_op.add_column(sa.Column('prime_sequence_verified', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        if 'prime_sequence_verified_at' not in cols:
            batch_op.add_column(sa.Column('prime_sequence_verified_at', sa.DateTime(), nullable=True))

    # Update Round 2 metadata in round_states table if present
    op.execute(
        "UPDATE round_states SET "
        "name = 'Cabo - The Memory Heist', "
        "codename = 'ROUND_2_CABO_THE_MEMORY_HEIST', "
        "initial_teams_count = 16, "
        "qualifying_teams_count = 8 "
        "WHERE id = 2"
    )


def downgrade() -> None:
    with op.batch_alter_table('final_code_records') as batch_op:
        batch_op.drop_column('prime_sequence_verified_at')
        batch_op.drop_column('prime_sequence_verified')
        batch_op.drop_column('echo_ho_verified_at')
        batch_op.drop_column('echo_ho_verified')
        batch_op.drop_column('echo_c_verified_at')
        batch_op.drop_column('echo_c_verified')
        batch_op.drop_column('echo_e_verified_at')
        batch_op.drop_column('echo_e_verified')
