"""update_round4_legal_battle_spec

Revision ID: 6e3a9f34c1b5
Revises: 5d2f7a91b8e4
Create Date: 2026-10-05 22:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6e3a9f34c1b5'
down_revision = '5d2f7a91b8e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Update round4_judge_scores
    js_cols = [c['name'] for c in inspector.get_columns('round4_judge_scores')]
    with op.batch_alter_table('round4_judge_scores') as batch_op:
        if 'is_locked' not in js_cols:
            batch_op.add_column(sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        if 'locked_at' not in js_cols:
            batch_op.add_column(sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True))
        if 'locked_by' not in js_cols:
            batch_op.add_column(sa.Column('locked_by', sa.String(255), nullable=True))
        if 'correction_notes' not in js_cols:
            batch_op.add_column(sa.Column('correction_notes', sa.Text(), nullable=True))
        if 'corrected_by' not in js_cols:
            batch_op.add_column(sa.Column('corrected_by', sa.String(255), nullable=True))
        if 'corrected_at' not in js_cols:
            batch_op.add_column(sa.Column('corrected_at', sa.DateTime(timezone=True), nullable=True))

    # 2. Update round4_stages
    st_cols = [c['name'] for c in inspector.get_columns('round4_stages')]
    with op.batch_alter_table('round4_stages') as batch_op:
        if 'timekeeper_name' not in st_cols:
            batch_op.add_column(sa.Column('timekeeper_name', sa.String(255), nullable=True))
        if 'time_violations_notes' not in st_cols:
            batch_op.add_column(sa.Column('time_violations_notes', sa.Text(), nullable=True))
        if 'penalty_seconds' not in st_cols:
            batch_op.add_column(sa.Column('penalty_seconds', sa.Integer(), nullable=True, server_default=sa.text('0')))

    # 3. Update round4_agent_guesses
    ag_cols = [c['name'] for c in inspector.get_columns('round4_agent_guesses')]
    with op.batch_alter_table('round4_agent_guesses') as batch_op:
        if 'guesses_json' not in ag_cols:
            batch_op.add_column(sa.Column('guesses_json', sa.JSON(), nullable=True))
        if 'total_guesses' not in ag_cols:
            batch_op.add_column(sa.Column('total_guesses', sa.Integer(), nullable=False, server_default=sa.text('0')))
        if 'correct_guesses' not in ag_cols:
            batch_op.add_column(sa.Column('correct_guesses', sa.Integer(), nullable=False, server_default=sa.text('0')))
        if 'wrong_guesses' not in ag_cols:
            batch_op.add_column(sa.Column('wrong_guesses', sa.Integer(), nullable=False, server_default=sa.text('0')))

    # 4. Update round_states for Round 4: 4 finalists, 2 semifinal matchups
    op.execute(
        "UPDATE round_states SET "
        "initial_teams_count = 4, "
        "qualifying_teams_count = 1, "
        "description = '4 finalist squads face off in 2 semifinal legal battles. Official 100-point rubric with multi-round final score integration.' "
        "WHERE id = 4"
    )

    # 5. Update round4_config
    op.execute(
        "UPDATE round4_config SET "
        "advancing_teams_count = 1, "
        "guessing_points_for_correct = 30.0, "
        "guessing_points_for_incorrect = -20.0, "
        "is_guessing_rules_configured = 1 "
        "WHERE id = 1"
    )


def downgrade() -> None:
    pass
