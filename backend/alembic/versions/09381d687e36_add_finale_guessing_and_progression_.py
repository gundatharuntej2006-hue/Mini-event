"""add_finale_guessing_and_progression_columns

Revision ID: 09381d687e36
Revises: 1d7dc59f4a11
Create Date: 2026-09-30 13:35:10.703307

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09381d687e36'
down_revision: Union[str, None] = '1d7dc59f4a11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('finale_config') as batch_op:
        batch_op.add_column(sa.Column('advancing_teams_count', sa.Integer(), nullable=True, server_default=sa.text('3')))
        batch_op.add_column(sa.Column('min_guesses', sa.Integer(), nullable=False, server_default=sa.text('1')))
        batch_op.add_column(sa.Column('max_guesses', sa.Integer(), nullable=False, server_default=sa.text('3')))
        batch_op.add_column(sa.Column('correct_guess_points', sa.Float(), nullable=False, server_default=sa.text('15.0')))
        batch_op.add_column(sa.Column('wrong_guess_points', sa.Float(), nullable=False, server_default=sa.text('-10.0')))
        batch_op.add_column(sa.Column('carryover_wallet_percent', sa.Float(), nullable=False, server_default=sa.text('10.0')))
        batch_op.add_column(sa.Column('is_guessing_open', sa.Boolean(), nullable=False, server_default=sa.text('1')))
        batch_op.add_column(sa.Column('is_revealed', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('revealed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('revealed_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('is_top_four_revealed', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('top_four_revealed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('top_four_revealed_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('is_podium_revealed', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('podium_revealed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('podium_revealed_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('is_agents_revealed', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('agents_revealed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('agents_revealed_by', sa.String(length=100), nullable=True))
        batch_op.drop_column('agent_penalty_points_for_incorrect')
        batch_op.drop_column('agent_bonus_points_for_correct')


def downgrade() -> None:
    with op.batch_alter_table('finale_config') as batch_op:
        batch_op.add_column(sa.Column('agent_bonus_points_for_correct', sa.FLOAT(), nullable=True))
        batch_op.add_column(sa.Column('agent_penalty_points_for_incorrect', sa.FLOAT(), nullable=True))
        batch_op.drop_column('agents_revealed_by')
        batch_op.drop_column('agents_revealed_at')
        batch_op.drop_column('is_agents_revealed')
        batch_op.drop_column('podium_revealed_by')
        batch_op.drop_column('podium_revealed_at')
        batch_op.drop_column('is_podium_revealed')
        batch_op.drop_column('top_four_revealed_by')
        batch_op.drop_column('top_four_revealed_at')
        batch_op.drop_column('is_top_four_revealed')
        batch_op.drop_column('revealed_by')
        batch_op.drop_column('revealed_at')
        batch_op.drop_column('is_revealed')
        batch_op.drop_column('is_guessing_open')
        batch_op.drop_column('carryover_wallet_percent')
        batch_op.drop_column('wrong_guess_points')
        batch_op.drop_column('correct_guess_points')
        batch_op.drop_column('max_guesses')
        batch_op.drop_column('min_guesses')
        batch_op.drop_column('advancing_teams_count')

