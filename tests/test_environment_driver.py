from mobius.drivers.environment.config import (
    EnvironmentConfigDriver,
    EnvironmentConfigDriverMapper,
    EnvironmentResolvedConfigDriver,
)


def make_driver(monkeypatch, prefix="", sufix=""):
    monkeypatch.setenv("MOBIUS_TEST_USER", "alice")
    monkeypatch.setenv("PRE_MOBIUS_TEST_USER_POST", "bob")

    config = EnvironmentResolvedConfigDriver(
        "ENV", EnvironmentConfigDriver(prefix, sufix)
    )
    return config.initialize()


def test_resolve_plain_env(monkeypatch):
    driver = make_driver(monkeypatch)

    assert driver.resolve({"user": "MOBIUS_TEST_USER"}) == {"user": "alice"}


def test_resolve_with_prefix_and_sufix(monkeypatch):
    driver = make_driver(monkeypatch, prefix="PRE", sufix="POST")

    assert driver.resolve({"user": "MOBIUS_TEST_USER"}) == {"user": "bob"}


def test_missing_variable_resolves_to_none(monkeypatch):
    driver = make_driver(monkeypatch)

    assert driver.resolve({"user": "MOBIUS_TEST_MISSING"}) == {"user": None}


def test_mapper_builds_resolved_config():
    config = EnvironmentConfigDriverMapper.from_json(
        "ENV", {"kind": "ENV", "resolver": None, "properties": {}, "config": {}}
    )

    assert isinstance(config, EnvironmentResolvedConfigDriver)
    assert config.config.separator == "_"


def test_mapper_parses_separator(monkeypatch):
    monkeypatch.setenv("PRE__MOBIUS_TEST_USER", "carol")

    config = EnvironmentConfigDriverMapper.from_json(
        "ENV",
        {
            "kind": "ENV",
            "resolver": None,
            "config": {"prefix": "PRE", "separator": "__"},
        },
    )

    assert config.config.separator == "__"

    driver = config.initialize()
    assert driver.resolve({"user": "MOBIUS_TEST_USER"}) == {"user": "carol"}
