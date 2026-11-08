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
    profile_columns = {item["name"] for item in inspector.get_columns("axiom_profiles")}
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
        # Personal profile fields are deliberately optional. They enrich the
        # member directory without changing the authoritative event roster.
        if "phone_number" not in profile_columns:
            connection.execute(text("ALTER TABLE axiom_profiles ADD COLUMN IF NOT EXISTS phone_number VARCHAR(24)"))
        if "skills" not in profile_columns:
            connection.execute(text("ALTER TABLE axiom_profiles ADD COLUMN IF NOT EXISTS skills TEXT NOT NULL DEFAULT ''"))
        if "linkedin_url" not in profile_columns:
            connection.execute(text("ALTER TABLE axiom_profiles ADD COLUMN IF NOT EXISTS linkedin_url VARCHAR(320)"))
        # Remove every legacy uniqueness rule that limits how many projects an
        # author may publish. Earlier production revisions used generated
        # constraint names, so dropping two assumed names was not sufficient.
        # Keep only the request-id uniqueness used to make retries idempotent.
        legacy_constraints = connection.execute(text("""
            SELECT con.conname
            FROM pg_constraint AS con
            JOIN pg_class AS rel ON rel.oid = con.conrelid
            JOIN pg_namespace AS nsp ON nsp.oid = rel.relnamespace
            WHERE nsp.nspname = current_schema()
              AND rel.relname = 'axiom_problem_statements'
              AND con.contype = 'u'
              AND con.conname <> 'uq_axiom_project_publish_request'
              AND EXISTS (
                SELECT 1
                FROM unnest(con.conkey) AS key(attnum)
                JOIN pg_attribute AS att
                  ON att.attrelid = rel.oid AND att.attnum = key.attnum
                WHERE att.attname = 'mentor_account_id'
              )
        """)).scalars().all()
        for constraint_name in legacy_constraints:
            safe_name = constraint_name.replace('"', '""')
            connection.execute(text(
                'ALTER TABLE axiom_problem_statements '
                f'DROP CONSTRAINT IF EXISTS "{safe_name}"'
            ))

        # Some old deployments created a standalone unique index rather than
        # a constraint. Remove author/slot indexes but preserve idempotency.
        legacy_indexes = connection.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = current_schema()
              AND tablename = 'axiom_problem_statements'
              AND indexname <> 'uq_axiom_project_publish_request'
              AND indexdef ILIKE 'CREATE UNIQUE INDEX%'
              AND indexdef ILIKE '%mentor_account_id%'
        """)).scalars().all()
        for index_name in legacy_indexes:
            safe_name = index_name.replace('"', '""')
            connection.execute(text(f'DROP INDEX IF EXISTS "{safe_name}"'))
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_axiom_project_publish_request "
            "ON axiom_problem_statements (mentor_account_id, client_request_id)"
        ))
