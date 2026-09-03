import pytest

httpx = pytest.importorskip("httpx")

from mobius.drivers.consul.config import (  # noqa: E402
    ConsulConfigDriver,
    ConsulConfigDriverMapper,
    ConsulResolvedConfigDriver,
    ConsulUnresolvedConfigDriver,
)
from mobius.drivers.consul.driver import ConsulDriver  # noqa: E402


KV = {
    "app/prod/PG_USER": "app",
    "app/prod/PG_PASSWORD": "s3cret",
    "flat-key": "flat-value",
    "empty": "",
}


def kv_handler(request: httpx.Request) -> httpx.Response:
    key = request.url.path.removeprefix("/v1/kv/")

    if key not in KV:
        return httpx.Response(404)

    return httpx.Response(200, text=KV[key])


def make_driver(prefix="", token=None):
    config = ConsulConfigDriver(
        "http://consul.local:8500", token, prefix, connect_timeout=5
    )
    return ConsulDriver("consul", config, transport=httpx.MockTransport(kv_handler))


def test_get_returns_raw_value():
    assert make_driver().get("flat-key") == "flat-value"


def test_get_missing_key_returns_none():
    assert make_driver().get("nope") is None


def test_get_empty_value():
    assert make_driver().get("empty") == ""


def test_prefix_is_joined_with_slash():
    assert make_driver(prefix="app/prod").get("PG_USER") == "app"
    assert make_driver(prefix="app/prod/").get("PG_USER") == "app"


def test_resolve_maps_properties():
    driver = make_driver(prefix="app/prod")

    resolved = driver.resolve({"user": "PG_USER", "password": "PG_PASSWORD"})

    assert resolved == {"user": "app", "password": "s3cret"}


def test_token_is_sent_as_header():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["token"] = request.headers.get("X-Consul-Token")
        return httpx.Response(200, text="value")

    config = ConsulConfigDriver("http://consul.local:8500", "secret-token", "", 5)
    driver = ConsulDriver("consul", config, transport=httpx.MockTransport(handler))

    driver.get("key")

    assert seen["token"] == "secret-token"


def test_server_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    config = ConsulConfigDriver("http://consul.local:8500", None, "", 5)
    driver = ConsulDriver("consul", config, transport=httpx.MockTransport(handler))

    with pytest.raises(httpx.HTTPStatusError):
        driver.get("key")


def test_config_str_does_not_leak_token():
    config = ConsulConfigDriver("http://consul.local:8500", "secret-token", "", 5)

    assert "secret-token" not in str(config)


def test_mapper_without_resolver_returns_resolved():
    config = ConsulConfigDriverMapper.from_json(
        "consul",
        {
            "kind": "CONSUL",
            "resolver": None,
            "config": {"address": "http://consul.local:8500"},
        },
    )

    assert isinstance(config, ConsulResolvedConfigDriver)
    assert config.config.address == "http://consul.local:8500"
    assert config.config.token is None
    assert config.config.prefix == ""
    assert config.config.connect_timeout == 10


def test_mapper_with_resolver_returns_unresolved_and_resolves():
    unresolved = ConsulConfigDriverMapper.from_json(
        "consul",
        {
            "kind": "CONSUL",
            "resolver": "ENV",
            "properties": {"token": "CONSUL_TOKEN", "server": "CONSUL_SERVER"},
            "config": {
                "address": "http://%(server)s",
                "token": "%(token)s",
                "prefix": "app/prod",
            },
        },
    )

    assert isinstance(unresolved, ConsulUnresolvedConfigDriver)

    resolved = unresolved.resolve(
        {"token": "secret-token", "server": "consul.local:8500"}
    )

    assert resolved.config.address == "http://consul.local:8500"
    assert resolved.config.token == "secret-token"
    assert resolved.config.prefix == "app/prod"
