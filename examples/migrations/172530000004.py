"""Cross-storage migration: backfill a PostgreSQL table from MongoDB
documents — the kind of migration single-storage tools cannot express.

Batched reads keep memory flat; the executemany + final commit keeps the
Postgres side all-or-nothing even though Mongo is read live.
"""
from mobius import Migration
from mobius.commons.data import chunk


class Migration172530000004(Migration):
    def validate(self):
        with self.manager.get("db") as connection:
            row = connection.execute("SELECT to_regclass('customers')").fetchone()
            if row[0] is None:
                raise ValueError("customers table missing - run 172530000001 first")

    def execute(self):
        with self.manager.get("documents") as client:
            profiles = list(
                client.get_default_database().profiles.find(
                    {}, {"_id": 1, "email": 1, "plan": 1}
                )
            )

        with self.manager.get("db") as connection:
            for batch in chunk(profiles, 500):
                connection.cursor().executemany(
                    """
                    INSERT INTO customers (id, email, plan)
                    VALUES (%(_id)s, %(email)s, %(plan)s)
                    ON CONFLICT (id) DO UPDATE SET plan = EXCLUDED.plan
                    """,
                    batch,
                )
            connection.commit()

    def description(self) -> str:
        return "backfill customers from mongo profiles"
