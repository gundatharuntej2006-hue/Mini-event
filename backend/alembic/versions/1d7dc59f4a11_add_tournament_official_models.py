"""add_tournament_official_models

Revision ID: 1d7dc59f4a11
Revises: e8464c1e0f9b
Create Date: 2026-09-23 18:07:44.825078

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d7dc59f4a11'
down_revision: Union[str, None] = 'e8464c1e0f9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Team Wallets
    op.create_table(
        'team_wallets',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('current_balance', sa.Numeric(precision=12, scale=2, asdecimal=False), nullable=False),
        sa.Column('total_earned', sa.Numeric(precision=12, scale=2, asdecimal=False), nullable=False),
        sa.Column('total_spent', sa.Numeric(precision=12, scale=2, asdecimal=False), nullable=False),
        sa.Column('total_penalties', sa.Numeric(precision=12, scale=2, asdecimal=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_team_wallets_team_id'), 'team_wallets', ['team_id'], unique=True)

    # 2. Wallet Transactions
    op.create_table(
        'wallet_transactions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('wallet_id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('transaction_type', sa.Enum('INITIAL_BALANCE', 'ROUND1_REWARD', 'ROUND2_REWARD', 'AGENT_TASK_REWARD', 'PENALTY', 'BLACK_MARKET_PURCHASE', 'REVERSAL', 'ADJUSTMENT', name='wallet_tx_type_enum', create_constraint=True), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2, asdecimal=False), nullable=False),
        sa.Column('balance_before', sa.Numeric(precision=12, scale=2, asdecimal=False), nullable=False),
        sa.Column('balance_after', sa.Numeric(precision=12, scale=2, asdecimal=False), nullable=False),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('reference_id', sa.String(length=100), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('is_reversed', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('reversal_id', sa.String(length=36), nullable=True),
        sa.Column('reversed_transaction_id', sa.String(length=36), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['wallet_id'], ['team_wallets.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wallet_transactions_team_id'), 'wallet_transactions', ['team_id'], unique=False)
    op.create_index(op.f('ix_wallet_transactions_wallet_id'), 'wallet_transactions', ['wallet_id'], unique=False)

    # 3. Cabo Table Assignments
    op.create_table(
        'cabo_table_assignments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('game_number', sa.Integer(), nullable=False),
        sa.Column('table_number', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('seat_position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('game_number IN (1, 2, 3)', name='ck_cabo_assignment_game_number'),
        sa.CheckConstraint('table_number >= 1 AND table_number <= 24', name='ck_cabo_assignment_table_number'),
        sa.CheckConstraint('seat_position >= 1 AND seat_position <= 5', name='ck_cabo_assignment_seat_position'),
        sa.ForeignKeyConstraint(['participant_id'], ['participants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_number', 'participant_id', name='uq_cabo_game_participant'),
        sa.UniqueConstraint('game_number', 'table_number', 'seat_position', name='uq_cabo_game_table_seat'),
        sa.UniqueConstraint('game_number', 'table_number', 'team_id', name='uq_cabo_game_table_team')
    )
    op.create_index(op.f('ix_cabo_table_assignments_game_number'), 'cabo_table_assignments', ['game_number'], unique=False)
    op.create_index(op.f('ix_cabo_table_assignments_participant_id'), 'cabo_table_assignments', ['participant_id'], unique=False)
    op.create_index(op.f('ix_cabo_table_assignments_table_number'), 'cabo_table_assignments', ['table_number'], unique=False)
    op.create_index(op.f('ix_cabo_table_assignments_team_id'), 'cabo_table_assignments', ['team_id'], unique=False)

    # 4. Cabo Player Scorecards
    op.create_table(
        'cabo_player_scorecards',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('game_number', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('table_assignment_id', sa.String(length=36), nullable=True),
        sa.Column('placement', sa.Integer(), nullable=False),
        sa.Column('placement_points', sa.Float(), nullable=False),
        sa.Column('final_card_hand_total', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('game_number IN (1, 2, 3)', name='ck_cabo_scorecard_game_number'),
        sa.CheckConstraint('placement >= 1 AND placement <= 5', name='ck_cabo_scorecard_placement'),
        sa.ForeignKeyConstraint(['participant_id'], ['participants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['table_assignment_id'], ['cabo_table_assignments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_number', 'participant_id', name='uq_cabo_scorecard_game_participant')
    )
    op.create_index(op.f('ix_cabo_player_scorecards_game_number'), 'cabo_player_scorecards', ['game_number'], unique=False)
    op.create_index(op.f('ix_cabo_player_scorecards_participant_id'), 'cabo_player_scorecards', ['participant_id'], unique=False)
    op.create_index(op.f('ix_cabo_player_scorecards_table_assignment_id'), 'cabo_player_scorecards', ['table_assignment_id'], unique=False)
    op.create_index(op.f('ix_cabo_player_scorecards_team_id'), 'cabo_player_scorecards', ['team_id'], unique=False)

    # 5. Secret Agent Dossiers
    op.create_table(
        'secret_agent_dossiers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('participant_id', sa.String(length=36), nullable=False),
        sa.Column('codename', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'COMPROMISED', 'REVEALED', 'DEACTIVATED', name='agent_dossier_status_enum', create_constraint=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['participant_id'], ['participants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_secret_agent_dossiers_participant_id'), 'secret_agent_dossiers', ['participant_id'], unique=True)
    op.create_index(op.f('ix_secret_agent_dossiers_team_id'), 'secret_agent_dossiers', ['team_id'], unique=True)

    # 6. Secret Agent Tasks
    op.create_table(
        'secret_agent_tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('dossier_id', sa.String(length=36), nullable=False),
        sa.Column('task_description', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('ASSIGNED', 'SUBMITTED', 'VERIFIED', 'REJECTED', 'CANCELLED', name='agent_task_status_enum', create_constraint=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence_reference', sa.Text(), nullable=True),
        sa.Column('organizer_id', sa.String(length=255), nullable=True),
        sa.Column('reward_points', sa.Float(), nullable=False),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['dossier_id'], ['secret_agent_dossiers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_secret_agent_tasks_dossier_id'), 'secret_agent_tasks', ['dossier_id'], unique=False)

    # 7. Final Code Records
    op.create_table(
        'final_code_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('fragment_1_status', sa.Enum('PENDING', 'RECOVERED', 'PURCHASED', 'MISSING', name='fragment_status_enum', create_constraint=True), nullable=False),
        sa.Column('fragment_1_value', sa.String(length=255), nullable=True),
        sa.Column('fragment_1_discovered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fragment_2_status', sa.Enum('PENDING', 'RECOVERED', 'PURCHASED', 'MISSING', name='fragment_status_enum', create_constraint=False), nullable=False),
        sa.Column('fragment_2_value', sa.String(length=255), nullable=True),
        sa.Column('fragment_2_discovered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('final_code_assembled', sa.String(length=255), nullable=True),
        sa.Column('final_code_verified', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by', sa.String(length=255), nullable=True),
        sa.Column('verification_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_final_code_records_team_id'), 'final_code_records', ['team_id'], unique=True)

    # 8. Black Market Purchases
    op.create_table(
        'black_market_purchases',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('asset_type', sa.Enum('MISSING_CODE_FRAGMENT', 'EXTRA_PREP_TIME', 'EXTRA_WITNESS_QUESTION', 'AGENT_INTEL', 'CUSTOM', name='bm_asset_type_enum', create_constraint=True), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('transaction_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.Enum('COMPLETED', 'REFUNDED', 'PENDING', name='bm_purchase_status_enum', create_constraint=True), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('purchased_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('purchased_by', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['transaction_id'], ['wallet_transactions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_black_market_purchases_team_id'), 'black_market_purchases', ['team_id'], unique=False)
    op.create_index(op.f('ix_black_market_purchases_transaction_id'), 'black_market_purchases', ['transaction_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_black_market_purchases_transaction_id'), table_name='black_market_purchases')
    op.drop_index(op.f('ix_black_market_purchases_team_id'), table_name='black_market_purchases')
    op.drop_table('black_market_purchases')

    op.drop_index(op.f('ix_final_code_records_team_id'), table_name='final_code_records')
    op.drop_table('final_code_records')

    op.drop_index(op.f('ix_secret_agent_tasks_dossier_id'), table_name='secret_agent_tasks')
    op.drop_table('secret_agent_tasks')

    op.drop_index(op.f('ix_secret_agent_dossiers_team_id'), table_name='secret_agent_dossiers')
    op.drop_index(op.f('ix_secret_agent_dossiers_participant_id'), table_name='secret_agent_dossiers')
    op.drop_table('secret_agent_dossiers')

    op.drop_index(op.f('ix_cabo_player_scorecards_team_id'), table_name='cabo_player_scorecards')
    op.drop_index(op.f('ix_cabo_player_scorecards_table_assignment_id'), table_name='cabo_player_scorecards')
    op.drop_index(op.f('ix_cabo_player_scorecards_participant_id'), table_name='cabo_player_scorecards')
    op.drop_index(op.f('ix_cabo_player_scorecards_game_number'), table_name='cabo_player_scorecards')
    op.drop_table('cabo_player_scorecards')

    op.drop_index(op.f('ix_cabo_table_assignments_team_id'), table_name='cabo_table_assignments')
    op.drop_index(op.f('ix_cabo_table_assignments_table_number'), table_name='cabo_table_assignments')
    op.drop_index(op.f('ix_cabo_table_assignments_participant_id'), table_name='cabo_table_assignments')
    op.drop_index(op.f('ix_cabo_table_assignments_game_number'), table_name='cabo_table_assignments')
    op.drop_table('cabo_table_assignments')

    op.drop_index(op.f('ix_wallet_transactions_wallet_id'), table_name='wallet_transactions')
    op.drop_index(op.f('ix_wallet_transactions_team_id'), table_name='wallet_transactions')
    op.drop_table('wallet_transactions')

    op.drop_index(op.f('ix_team_wallets_team_id'), table_name='team_wallets')
    op.drop_table('team_wallets')
