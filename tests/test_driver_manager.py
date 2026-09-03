from typing import Any, Dict

import pytest

from mobius.commons.driver import IDriver
from mobius.commons.logger.service import IStateDriver
from mobius.commons.resolver import IResolver
from mobius.commons.mapping import MappingException
from mobius.config import MobiusJsonMapper, MobiusSettings, MobiusSettingsJsonMapper
from mobius.drivers.manager import (
    DriverJsonMapper,
    DriverManager,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)


class FakeResolverDriver(IDriver, IResolver):
    def connection(self) -> Any:
        return None

    def close(self, connection: Any):
        pass

    def get(self, name: str) -> str:
        return f"resolved-{name}"

    def resolve(self, properties: Dict[str, str]) -> Dict[str, Any]:
        return {key: f"resolved-{value}" for key, value in properties.items()}


class NotAResolverDriver(IDriver):
    def connection(self) -> Any:
        return None

    def close(self, connection: Any):
        pass


class NoneResolverDriver(FakeResolverDriver):
    def resolve(self, properties: Dict[str, str]) -> Dict[str, Any]:
        return {key: None for key in properties}


class StubResolvedConfig(DriverResolvedConfig):
    def __init__(self, name, driver=None, resolved_properties=None):
        super().__init__(name, None)
        self.driver = driver
        self.resolved_properties = resolved_properties

    def initialize(self):
        return self.driver


class StubUnresolvedConfig(DriverUnresolvedConfig):
    def resolve(self, resolved_properties) -> DriverResolvedConfig:
        return StubResolvedConfig(self.name, resolved_properties=resolved_properties)


def make_manager(sources):
    state = StubResolvedConfig("state")
    locker = StubResolvedConfig("locker")
    return DriverManager(state, locker, sources)


def test_unresolved_config_is_resolved_through_resolver():
    env = StubResolvedConfig("ENV", driver=FakeResolverDriver())
    db = StubUnresolvedConfig("db", "ENV", None, {"user": "DB_USER"})

    manager = make_manager([env, db])
    config = manager.get_config("db")

    assert isinstance(config, StubResolvedConfig)
    assert config.resolved_properties == {"user": "resolved-DB_USER"}
    # resolved config replaces the unresolved one
    assert manager.configs["db"] is config


def test_unresolvable_property_fails_closed():
    env = StubResolvedConfig("ENV", driver=NoneResolverDriver())
    db = StubUnresolvedConfig("db", "ENV", None, {"password": "PG_PASSWORD"})
    manager = make_manager([env, db])

    with pytest.raises(ValueError) as info:
        manager.get_config("db")

    assert "password (PG_PASSWORD)" in str(info.value)
    assert "ENV" in str(info.value)


def test_resolver_cannot_resolve_itself():
    db = StubUnresolvedConfig("db", "db", None, {})
    manager = make_manager([db])

    with pytest.raises(ValueError):
        manager.get_config("db")


def test_resolver_must_implement_iresolver():
    env = StubResolvedConfig("ENV", driver=NotAResolverDriver())
    db = StubUnresolvedConfig("db", "ENV", None, {})
    manager = make_manager([env, db])

    with pytest.raises(ValueError):
        manager.get_config("db")


def test_unknown_config_raises():
    manager = make_manager([])

    with pytest.raises(RuntimeError):
        manager.get_config("missing")


def test_resolve_all_resolves_every_source():
    env = StubResolvedConfig("ENV", driver=FakeResolverDriver())
    db = StubUnresolvedConfig("db", "ENV", None, {})

    manager = make_manager([env, db])
    manager.resolve_all()

    assert all(
        isinstance(config, DriverResolvedConfig)
        for config in manager.configs.values()
    )


def test_get_state_driver_rejects_non_state_driver():
    state = StubResolvedConfig("state", driver=NotAResolverDriver())
    manager = DriverManager(state, StubResolvedConfig("locker"), [])

    with pytest.raises(ValueError):
        manager.get_state_driver()


class FakeStateDriver(IStateDriver):
    def get_logs_repository(self):
        return "logs-repo"


def test_get_state_driver_returns_and_caches():
    state = StubResolvedConfig("state", driver=FakeStateDriver())
    manager = DriverManager(state, StubResolvedConfig("locker"), [])

    driver = manager.get_state_driver()

    assert isinstance(driver, FakeStateDriver)
    assert manager.get_state_driver() is driver


class StubMapper(IConfigDriverMapper):
    JSON_KIND = "FAKE"
    KIND = IDriverConfig

    @classmethod
    def from_context(cls, name, context):
        return StubResolvedConfig(name)


def test_json_mapper_dispatches_by_kind():
    mapper = DriverJsonMapper()
    mapper.register(StubMapper)

    config = mapper.from_json("db", {"kind": "FAKE"})

    assert isinstance(config, StubResolvedConfig)
    assert config.name == "db"


def test_json_mapper_rejects_duplicate_kind():
    mapper = DriverJsonMapper()
    mapper.register(StubMapper)

    with pytest.raises(ValueError):
        mapper.register(StubMapper)


def test_json_mapper_rejects_non_object():
    mapper = DriverJsonMapper()

    with pytest.raises(MappingException):
        mapper.from_json("db", "not-a-dict")


def test_json_mapper_reports_unknown_kind_with_segment():
    mapper = DriverJsonMapper()
    mapper.register(StubMapper)

    with pytest.raises(MappingException) as info:
        mapper.from_json("db", {"kind": "NOPE"})

    (segment,) = info.value.errors
    assert str(segment) == "$.kind"


def test_mobius_json_mapper_maps_full_config():
    mapper = DriverJsonMapper()
    mapper.register(StubMapper)

    raw = {
        "state": {"kind": "FAKE"},
        "locker": {"kind": "FAKE"},
        "sources": {"db": {"kind": "FAKE"}, "queue": {"kind": "FAKE"}},
    }

    config = MobiusJsonMapper.from_json(raw, mapper)

    assert config.state.name == "state"
    assert config.locker.name == "locker"
    assert set(config.sources) == {"db", "queue"}
    # no "settings" block: defaults apply
    assert config.settings.lock_ttl == 90
    assert config.settings.lock_retry_interval == 1.0


def test_mobius_json_mapper_maps_settings():
    mapper = DriverJsonMapper()
    mapper.register(StubMapper)

    raw = {
        "settings": {"lockTtl": 30, "lockRetryInterval": 0.5},
        "state": {"kind": "FAKE"},
        "locker": {"kind": "FAKE"},
        "sources": {},
    }

    config = MobiusJsonMapper.from_json(raw, mapper)

    assert config.settings.lock_ttl == 30
    assert config.settings.lock_retry_interval == 0.5


def test_settings_partial_block_keeps_defaults():
    settings = MobiusSettingsJsonMapper.from_json({"lockTtl": 120})

    assert settings.lock_ttl == 120
    assert settings.lock_retry_interval == 1.0


@pytest.mark.parametrize(
    "raw",
    [{"lockTtl": 0}, {"lockTtl": -5}, {"lockRetryInterval": 0}],
)
def test_settings_reject_non_positive_values(raw):
    with pytest.raises(MappingException):
        MobiusSettingsJsonMapper.from_json(raw)


def test_settings_reject_non_object():
    with pytest.raises(MappingException):
        MobiusSettingsJsonMapper.from_json("not-a-dict")


def test_mobius_json_mapper_accumulates_errors_across_drivers():
    mapper = DriverJsonMapper()
    mapper.register(StubMapper)

    raw = {
        "state": {"kind": "FAKE"},
        "locker": {},  # missing kind
        "sources": {
            "db": {"kind": "UNKNOWN"},
            "queue": "not-an-object",
        },
        "settings": {"lockTtl": -1},
    }

    with pytest.raises(MappingException) as info:
        MobiusJsonMapper.from_json(raw, mapper)

    segments = {str(segment) for segment in info.value.errors}
    assert segments == {
        "$.locker.kind",
        "$.sources.db.kind",
        "$.sources.queue",
        "$.settings.lockTtl",
    }


def test_settings_defaults():
    settings = MobiusSettings()

    assert settings.lock_ttl == 90
    assert settings.lock_retry_interval == 1.0
