"""Plain SQL schema + seed data on a PostgreSQL source.

The connection has autocommit off: nothing is persisted unless the
migration commits, so a crash halfway leaves the database untouched.
"""
from mobius import Migration, MigrationFailedException


class Migration172530000001(Migration):
    def validate(self):
        # validate() runs before execute(); raise here to abort
        # before any writes happen
        with self.manager.get("db") as connection:
            row = connection.execute("SELECT current_database()").fetchone()
            if row[0] != "app":
                raise MigrationFailedException(f"Wrong database: {row[0]}")

    def execute(self):
        with self.manager.get("db") as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id bigint PRIMARY KEY,
                    email text NOT NULL UNIQUE,
                    plan text NOT NULL DEFAULT 'free'
                )
                """
            )
            connection.execute(
                """
                INSERT INTO customers (id, email, plan)
                VALUES (1, 'demo@example.com', 'trial')
                ON CONFLICT (id) DO NOTHING
                """
            )
            connection.commit()

    def description(self) -> str:
        return "create customers table and seed the demo account"
