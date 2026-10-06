"""add_round1_started_at_to_config

Revision ID: 7f4a1c92d5e6
Revises: 6e3a9f34c1b5
Create Date: 2026-10-06 10:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7f4a1c92d5e6'
down_revision = '6e3a9f34c1b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    cols = [c['name'] for c in inspector.get_columns('round1_config')]
    with op.batch_alter_table('round1_config') as batch_op:
        if 'started_at' not in cols:
            batch_op.add_column(sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
        if 'started_by' not in cols:
            batch_op.add_column(sa.Column('started_by', sa.String(100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('round1_config') as batch_op:
        batch_op.drop_column('started_by')
        batch_op.drop_column('started_at')
