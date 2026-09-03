"""Document transformation on a MongoDB source, skipping when there is
nothing to do.

A migration that raises MigrationSkippedException is recorded as Skipped —
a success: it will not run again.
"""
from mobius import Migration, MigrationSkippedException


class Migration172530000002(Migration):
    def validate(self):
        pass

    def execute(self):
        with self.manager.get("documents") as client:
            orders = client.get_default_database().orders

            outdated = {"schema_version": {"$lt": 2}}

            if orders.count_documents(outdated) == 0:
                raise MigrationSkippedException("all orders already at v2")

            orders.update_many(
                outdated,
                {
                    "$set": {"schema_version": 2},
                    "$rename": {"client": "customer"},
                },
            )

    def description(self) -> str:
        return "rename orders.client to orders.customer (schema v2)"
