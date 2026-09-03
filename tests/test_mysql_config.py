import pytest

pymysql = pytest.importorskip("pymysql")

from mobius.commons.locker.service import ILockerDriver  # noqa: E402
from mobius.commons.logger.service import IStateDriver  # noqa: E402
from mobius.drivers.mysql.config import (  # noqa: E402
    MySqlConfigDriverMapper,
    MysqlResolvedConfigDriver,
    MysqlUnresolvedConfigDriver,
)
from mobius.drivers.mysql.driver import MySqlDriver  # noqa: E402


def test_mapper_without_resolver_returns_resolved():
    config = MySqlConfigDriverMapper.from_json(
        "db",
        {
            "kind": "MYSQL",
            "resolver": None,
            "config": {"host": "localhost", "database": "mobius", "user": "app"},
        },
    )

    assert isinstance(config, MysqlResolvedConfigDriver)
    assert config.config.host == "localhost"
    assert config.config.port == 3306
    assert config.config.connect_timeout == 10


def test_mapper_with_resolver_returns_unresolved():
    config = MySqlConfigDriverMapper.from_json(
        "db",
        {
            "kind": "MYSQL",
            "resolver": "ENV",
            "properties": {"user": "MYSQL_USER"},
            "config": {"host": "%(server)s", "user": "%(user)s"},
        },
    )

    assert isinstance(config, MysqlUnresolvedConfigDriver)


def test_resolve_interpolates_properties():
    unresolved = MySqlConfigDriverMapper.from_json(
        "db",
        {
            "kind": "MYSQL",
            "resolver": "ENV",
            "properties": {
                "server": "MYSQL_SERVER",
                "user": "MYSQL_USER",
                "password": "MYSQL_PASSWORD",
            },
            "config": {
                "host": "%(server)s",
                "database": "mobius",
                "user": "%(user)s",
                "password": "%(password)s",
                "port": 3307,
            },
        },
    )

    resolved = unresolved.resolve(
        {"server": "db.local", "user": "app", "password": "s3cret"}
    )

    assert resolved.config.host == "db.local"
    assert resolved.config.user == "app"
    assert resolved.config.password == "s3cret"
    assert resolved.config.port == 3307
    assert resolved.config.database == "mobius"


def test_driver_implements_state_and_locker_interfaces():
    assert issubclass(MySqlDriver, IStateDriver)
    assert issubclass(MySqlDriver, ILockerDriver)
