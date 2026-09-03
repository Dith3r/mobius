"""Statement that cannot run inside a transaction.

CREATE INDEX CONCURRENTLY refuses to run in a transaction block, so this
migration uses the "db_autocommit" source — the same database, configured
with "autocommit": true. Keep such statements in their own migration:
with autocommit there is no rollback if a later statement fails.
"""
from mobius import Migration


class Migration172530000005(Migration):
    def validate(self):
        pass

    def execute(self):
        with self.manager.get("db_autocommit") as connection:
            connection.execute(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS customers_plan_idx "
                "ON customers (plan)"
            )

    def description(self) -> str:
        return "index customers.plan (concurrently)"
