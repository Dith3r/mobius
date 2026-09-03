import pytest

pytest.importorskip("psycopg")
confluent_kafka = pytest.importorskip("confluent_kafka")

import psycopg  # noqa: E402
from confluent_kafka.admin import AdminClient  # noqa: E402

from mobius.commands.migrate import MigrateCommand  # noqa: E402
from mobius.commons.locker.service import Locker  # noqa: E402
from mobius.commons.logger.model import Succeed  # noqa: E402
from mobius.commons.logger.service import Logger  # noqa: E402
from mobius.config import MobiusSettings  # noqa: E402
from mobius.drivers.kafka.config import (  # noqa: E402
    KafkaConfigDriver,
    KafkaResolvedConfigDriver,
)
from mobius.drivers.manager import DriverManager  # noqa: E402
from mobius.drivers.postgres.config import (  # noqa: E402
    PostgresConfigDriver,
    PostgresResolvedConfigDriver,
)


TOPIC = "mobius-migrated"

MIGRATION_POSTGRES = """
from mobius import Migration


class Migration1100(Migration):
    def validate(self):
        pass

    def execute(self):
        with self.manager.get("db") as connection:
            connection.execute(
                "CREATE TABLE people (id int PRIMARY KEY, name text)"
            )
            connection.execute(
                "INSERT INTO people (id, name) VALUES (1, 'ada'), (2, 'grace')"
            )
            connection.commit()

    def description(self):
        return "seed people"
"""

MIGRATION_REDPANDA = f"""
from confluent_kafka.admin import NewTopic

from mobius import Migration


class Migration1200(Migration):
    def validate(self):
        pass

    def execute(self):
        with self.manager.get("queue") as admin:
            futures = admin.create_topics(
                [NewTopic("{TOPIC}", num_partitions=1, replication_factor=1)]
            )
            for future in futures.values():
                future.result(30)

    def description(self):
        return "create events topic"
"""


def postgres_config(name, url):
    return PostgresResolvedConfigDriver(
        name, PostgresConfigDriver(url, connect_timeout=10, autocommit=False)
    )


def clean_database(url):
    with psycopg.connect(url, autocommit=True) as connection:
        for table in ("locks", "logs", "people"):
            connection.execute(f"DROP TABLE IF EXISTS {table}")


@pytest.fixture()
def command(postgres_url, redpanda_bootstrap):
    clean_database(postgres_url)

    manager = DriverManager(
        postgres_config("state", postgres_url),
        postgres_config("locker", postgres_url),
        [
            postgres_config("db", postgres_url),
            KafkaResolvedConfigDriver("queue", KafkaConfigDriver(redpanda_bootstrap)),
        ],
    )

    logger = Logger(manager.get_state_driver().get_logs_repository())
    locker = Locker(manager.get_locker_driver().get_locks_repository())

    return MigrateCommand(manager, logger, locker, MobiusSettings())


def test_migrations_against_real_postgres_and_redpanda(
    command, postgres_url, redpanda_bootstrap, tmp_path
):
    (tmp_path / "1100.py").write_text(MIGRATION_POSTGRES)
    (tmp_path / "1200.py").write_text(MIGRATION_REDPANDA)

    command.execute(str(tmp_path), ignore_hash=False, no_wait=True)

    # migration effects landed in the source systems
    with psycopg.connect(postgres_url) as connection:
        people = connection.execute("SELECT id, name FROM people ORDER BY id").fetchall()
    assert people == [(1, "ada"), (2, "grace")]

    admin = AdminClient({"bootstrap.servers": redpanda_bootstrap})
    topics = admin.list_topics(timeout=10).topics
    assert TOPIC in topics

    # state log records both migrations as succeeded
    logs = command.logger.fetch_by_id([1100, 1200])
    assert {log.id: log.state for log in logs} == {1100: Succeed, 1200: Succeed}

    # lock was released
    with psycopg.connect(postgres_url) as connection:
        assert connection.execute("SELECT count(*) FROM locks").fetchone()[0] == 0

    # a second run is a no-op: CREATE TABLE would fail if migrations re-ran
    command.execute(str(tmp_path), ignore_hash=False, no_wait=True)
