import pytest

psycopg = pytest.importorskip("psycopg")

from mobius.commons.locker.service import ILockerDriver  # noqa: E402
from mobius.commons.logger.service import IStateDriver  # noqa: E402
from mobius.drivers.postgres.config import (  # noqa: E402
    PostgresConfigDriverMapper,
    PostgresResolvedConfigDriver,
    PostgresUnresolvedConfigDriver,
)
from mobius.drivers.postgres.driver import PostgresDriver  # noqa: E402


def test_mapper_without_resolver_returns_resolved():
    config = PostgresConfigDriverMapper.from_json(
        "db",
        {
            "kind": "POSTGRES",
            "resolver": None,
            "config": {"connectionUrl": "postgresql://localhost/db"},
        },
    )

    assert isinstance(config, PostgresResolvedConfigDriver)
    assert config.config.connection_url == "postgresql://localhost/db"
    assert config.config.connect_timeout == 10
    assert config.config.autocommit is False


def test_mapper_with_resolver_returns_unresolved():
    config = PostgresConfigDriverMapper.from_json(
        "db",
        {
            "kind": "POSTGRES",
            "resolver": "ENV",
            "properties": {"user": "PG_USER"},
            "config": {"connectionUrl": "postgresql://%(user)s@host/db"},
        },
    )

    assert isinstance(config, PostgresUnresolvedConfigDriver)


def test_resolve_interpolates_and_quotes_properties():
    unresolved = PostgresConfigDriverMapper.from_json(
        "db",
        {
            "kind": "POSTGRES",
            "resolver": "ENV",
            "properties": {"user": "PG_USER", "password": "PG_PASSWORD"},
            "config": {
                "connectionUrl": "postgresql://%(user)s:%(password)s@host/db",
                "connectTimeout": 5,
            },
        },
    )

    resolved = unresolved.resolve({"user": "app", "password": "p@ss"})

    assert resolved.config.connection_url == "postgresql://app:p%40ss@host/db"
    assert resolved.config.connect_timeout == 5


def test_driver_implements_state_and_locker_interfaces():
    assert issubclass(PostgresDriver, IStateDriver)
    assert issubclass(PostgresDriver, ILockerDriver)


def test_config_str_masks_password():
    config = PostgresConfigDriverMapper.from_json(
        "db",
        {
            "kind": "POSTGRES",
            "resolver": None,
            "config": {"connectionUrl": "postgresql://app:hunter2@db:5432/app"},
        },
    )

    assert "hunter2" not in str(config)
    assert "app:***@" in str(config)
