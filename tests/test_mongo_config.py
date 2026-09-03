import pytest

pymongo = pytest.importorskip("pymongo")

from mobius.drivers.mongo.config import (  # noqa: E402
    MongoConfigDriverMapper,
    MongoResolvedConfigDriver,
)


def make(config):
    return MongoConfigDriverMapper.from_json(
        "db", {"kind": "MONGO", "resolver": None, "config": config}
    )


def test_max_pool_size_accepts_string_number():
    # pre-mapping-refactor configs stored the number as a JSON string
    config = make({"connectionUrl": "mongodb://localhost/db", "maxPoolSize": "25"})

    assert isinstance(config, MongoResolvedConfigDriver)
    assert config.config.max_pool == 25


def test_max_pool_size_accepts_int():
    config = make({"connectionUrl": "mongodb://localhost/db", "maxPoolSize": 25})

    assert config.config.max_pool == 25


def test_config_str_masks_password():
    config = make(
        {"connectionUrl": "mongodb://app:hunter2@mongo:27017/db?authSource=admin"}
    )

    assert "hunter2" not in str(config)
    assert "app:***@" in str(config)
