import pytest

httpx = pytest.importorskip("httpx")
pytest.importorskip("psycopg")

from mobius.drivers.consul.config import (  # noqa: E402
    ConsulConfigDriver,
    ConsulResolvedConfigDriver,
)
from mobius.drivers.consul.driver import ConsulDriver  # noqa: E402
from mobius.drivers.manager import DriverManager, DriverResolvedConfig  # noqa: E402
from mobius.drivers.postgres.config import (  # noqa: E402
    PostgresConfigDriver,
    PostgresUnresolvedConfigDriver,
)


class StubConfig(DriverResolvedConfig):
    def __init__(self, name):
        super().__init__(name, None)

    def initialize(self):
        return None


@pytest.fixture(scope="module")
def seeded_consul(consul_address):
    keys = {
        "app/prod/PG_USER": "app",
        "app/prod/PG_PASSWORD": "s3cret",
        "app/prod/PG_SERVER": "db.local:5432",
    }

    with httpx.Client(base_url=consul_address) as client:
        for key, value in keys.items():
            assert client.put(f"/v1/kv/{key}", content=value).json() is True

    return consul_address


def make_driver(address, prefix=""):
    return ConsulDriver(
        "consul", ConsulConfigDriver(address, None, prefix, connect_timeout=10)
    )


def test_get_and_missing_key(seeded_consul):
    driver = make_driver(seeded_consul, prefix="app/prod")

    assert driver.get("PG_USER") == "app"
    assert driver.get("MISSING") is None


def test_resolve_properties(seeded_consul):
    driver = make_driver(seeded_consul, prefix="app/prod")

    resolved = driver.resolve({"user": "PG_USER", "password": "PG_PASSWORD"})

    assert resolved == {"user": "app", "password": "s3cret"}


def test_consul_resolves_driver_config_through_manager(seeded_consul):
    consul_config = ConsulResolvedConfigDriver(
        "consul",
        ConsulConfigDriver(seeded_consul, None, "app/prod", connect_timeout=10),
    )

    database = PostgresUnresolvedConfigDriver(
        "db",
        "consul",
        PostgresConfigDriver(
            "postgresql://%(user)s:%(password)s@%(server)s/mobius",
            connect_timeout=10,
            autocommit=False,
        ),
        {"user": "PG_USER", "password": "PG_PASSWORD", "server": "PG_SERVER"},
    )

    manager = DriverManager(StubConfig("state"), StubConfig("locker"), [consul_config, database])

    resolved = manager.get_config("db")

    assert (
        resolved.config.connection_url
        == "postgresql://app:s3cret@db.local%3A5432/mobius"
    )
