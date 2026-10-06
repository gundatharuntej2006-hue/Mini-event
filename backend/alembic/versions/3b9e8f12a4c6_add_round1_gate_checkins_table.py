"""add round1_gate_checkins table

Revision ID: 3b9e8f12a4c6
Revises: 2a8f9c10d3e5
Create Date: 2026-10-05 18:22:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3b9e8f12a4c6'
down_revision = '2a8f9c10d3e5'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Check if table already exists before creating
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "round1_gate_checkins" not in existing_tables:
        op.create_table(
            'round1_gate_checkins',
            sa.Column('id', sa.String(length=100), primary_key=True),
            sa.Column('team_id', sa.String(length=50), sa.ForeignKey('teams.id'), nullable=False),
            sa.Column('team_name', sa.String(length=100), nullable=False),
            sa.Column('round_number', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('gate_number', sa.Integer(), nullable=False),
            sa.Column('scanned_at', sa.DateTime(), nullable=False),
            sa.Column('is_duplicate', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='VERIFIED'),
            sa.Column('notes', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_round1_gate_checkins_team_id', 'round1_gate_checkins', ['team_id'])
        op.create_index('ix_round1_gate_checkins_gate_number', 'round1_gate_checkins', ['gate_number'])

def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "round1_gate_checkins" in existing_tables:
        op.drop_index('ix_round1_gate_checkins_gate_number', table_name='round1_gate_checkins')
        op.drop_index('ix_round1_gate_checkins_team_id', table_name='round1_gate_checkins')
        op.drop_table('round1_gate_checkins')
