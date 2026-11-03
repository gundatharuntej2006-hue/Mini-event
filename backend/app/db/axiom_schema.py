"""Small, idempotent production upgrade for Project Axiom statements.

`create_all()` creates missing tables but intentionally does not alter an
existing PostgreSQL table. This upgrade removes legacy author-slot constraints
without touching existing project briefs or preferences.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def upgrade_axiom_statement_schema(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        # Fresh SQLite test databases are created from the current model.
        return

    inspector = inspect(engine)
    if "axiom_problem_statements" not in inspector.get_table_names():
        return

    columns = {item["name"] for item in inspector.get_columns("axiom_problem_statements")}
    with engine.begin() as connection:
        if "statement_slot" not in columns:
            connection.execute(text(
                "ALTER TABLE axiom_problem_statements "
                "ADD COLUMN statement_slot INTEGER NOT NULL DEFAULT 1"
            ))
        if "client_request_id" not in columns:
            connection.execute(text(
                "ALTER TABLE axiom_problem_statements "
                "ADD COLUMN client_request_id VARCHAR(64)"
            ))
        # Remove legacy one- and two-statement author constraints. The open
        # project board deliberately permits unlimited briefs per publisher.
        connection.execute(text(
            "ALTER TABLE axiom_problem_statements "
            "DROP CONSTRAINT IF EXISTS axiom_problem_statements_mentor_account_id_key"
        ))
        connection.execute(text(
            "ALTER TABLE axiom_problem_statements "
            "DROP CONSTRAINT IF EXISTS uq_axiom_statement_author_slot"
        ))
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_axiom_project_publish_request "
            "ON axiom_problem_statements (mentor_account_id, client_request_id)"
        ))
