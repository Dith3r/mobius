"""Kafka topic creation — skip if the topic already exists.

The KAFKA source hands the migration a confluent_kafka AdminClient.
"""
from confluent_kafka.admin import NewTopic

from mobius import Migration, MigrationSkippedException


TOPIC = "customer-events"


class Migration172530000003(Migration):
    def validate(self):
        pass

    def execute(self):
        with self.manager.get("queue") as admin:
            if TOPIC in admin.list_topics(timeout=10).topics:
                raise MigrationSkippedException(f"topic {TOPIC} already exists")

            futures = admin.create_topics(
                [NewTopic(TOPIC, num_partitions=6, replication_factor=3)]
            )
            for future in futures.values():
                future.result(30)

    def description(self) -> str:
        return f"create {TOPIC} topic"
