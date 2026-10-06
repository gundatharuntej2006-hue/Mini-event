"""update_round3_black_market_and_approvals

Revision ID: 5d2f7a91b8e4
Revises: 4c1a8e23b9d0
Create Date: 2026-10-05 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d2f7a91b8e4'
down_revision = '4c1a8e23b9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('black_market_purchases')]

    with op.batch_alter_table('black_market_purchases') as batch_op:
        if 'approval_status' not in cols:
            batch_op.add_column(sa.Column('approval_status', sa.String(30), nullable=False, server_default=sa.text("'APPROVED'")))
        if 'first_approved_by' not in cols:
            batch_op.add_column(sa.Column('first_approved_by', sa.String(255), nullable=True))
        if 'first_approved_at' not in cols:
            batch_op.add_column(sa.Column('first_approved_at', sa.DateTime(), nullable=True))
        if 'second_approved_by' not in cols:
            batch_op.add_column(sa.Column('second_approved_by', sa.String(255), nullable=True))
        if 'second_approved_at' not in cols:
            batch_op.add_column(sa.Column('second_approved_at', sa.DateTime(), nullable=True))
        if 'notes' not in cols:
            batch_op.add_column(sa.Column('notes', sa.Text(), nullable=True))

    # Update Round 3 metadata in round_states table
    op.execute(
        "UPDATE round_states SET "
        "name = 'The Black Market', "
        "codename = 'ROUND_3_BLACK_MARKET', "
        "description = '8 squads navigate a volatile resource economy, trading assets and recovering code fragments. Top 4 qualify.', "
        "initial_teams_count = 8, "
        "qualifying_teams_count = 4, "
        "config_json = '{\"startingBalance\": 1000.0, \"codeFragmentsCount\": 4, \"allowNegativeBalance\": false, \"missingFragmentPenalty\": -350.0}' "
        "WHERE id = 3"
    )

    # Update Round 3 config
    op.execute(
        "UPDATE round3_config SET "
        "starting_balance = 1000.0, "
        "hidden_code_config = '{\"isRequiredForQualification\": true, \"requiredFragmentCount\": 4, \"isConfigured\": true, \"missingFragmentPenalty\": -350.0}' "
        "WHERE id = 1"
    )


def downgrade() -> None:
    with op.batch_alter_table('black_market_purchases') as batch_op:
        batch_op.drop_column('notes')
        batch_op.drop_column('second_approved_at')
        batch_op.drop_column('second_approved_by')
        batch_op.drop_column('first_approved_at')
        batch_op.drop_column('first_approved_by')
        batch_op.drop_column('approval_status')
