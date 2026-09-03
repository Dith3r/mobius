from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)
from mobius.drivers.postgres.driver import PostgresDriver


class PostgresConfigDriver(IDriverConfig):
    connection_url: Optional[str]
    connect_timeout: int
    autocommit: bool

    def __init__(
        self,
        connection_url: Optional[str],
        connect_timeout: int,
        autocommit: bool,
    ):
        self.connection_url = connection_url
        self.connect_timeout = connect_timeout
        self.autocommit = autocommit

    def __str__(self):
        return (
            f"{self.__class__.__name__}[connection_url={self.connection_url}, "
            f"connect_timeout={self.connect_timeout}, autocommit={self.autocommit}]"
        )


class PostgresResolvedConfigDriver(DriverResolvedConfig):
    config: PostgresConfigDriver

    def __init__(self, name: str, config: PostgresConfigDriver):
        super().__init__(name, config)

    def initialize(self) -> PostgresDriver:
        return PostgresDriver(
            self.name,
            self.config.connection_url,
            connect_timeout=self.config.connect_timeout,
            autocommit=self.config.autocommit,
        )

    def __str__(self):
        return f"{self.__class__.__name__}[name={self.name},config={self.config}]"


class PostgresUnresolvedConfigDriver(DriverUnresolvedConfig):
    config: PostgresConfigDriver

    def __init__(
        self,
        name: str,
        resolver: str,
        config: PostgresConfigDriver,
        properties: Dict[str, str],
    ):
        super().__init__(name, resolver, config, properties)

    def resolve(self, resolved_properties: Dict[str, Any]) -> DriverResolvedConfig:
        quoted = {
            key: quote_plus(str(value)) for key, value in resolved_properties.items()
        }

        postgres_config = PostgresConfigDriver(
            self.config.connection_url % quoted,
            connect_timeout=int(str(self.config.connect_timeout) % resolved_properties),
            autocommit=self.config.autocommit,
        )

        return PostgresResolvedConfigDriver(self.name, postgres_config)


class PostgresConfigDriverMapper(IConfigDriverMapper):
    __slots__ = ()
    JSON_KIND = "POSTGRES"
    KIND = PostgresConfigDriver

    class DEFAULT:
        __slots__ = ()
        CONNECT_TIMEOUT = 10
        AUTOCOMMIT = False

    class FIELDS(CommonDriverMapper.Fields):
        __slots__ = ()
        CONNECTION_URL = "connectionUrl"
        CONNECT_TIMEOUT = "connectTimeout"
        AUTOCOMMIT = "autocommit"

    @classmethod
    def from_json(cls, name: str, data: dict) -> IDriverConfig:
        _ = cls.FIELDS

        resolver = data[_.RESOLVER]
        config = data.get(_.CONFIG, {})
        properties = data.get(_.PROPERTIES, {})

        if not isinstance(config, dict):
            raise RuntimeError("Invalid config for driver %s", name)

        if not isinstance(properties, dict):
            raise RuntimeError("Invalid properties for driver %s", name)

        connection_url = config.get(_.CONNECTION_URL)
        connect_timeout = int(config.get(_.CONNECT_TIMEOUT, cls.DEFAULT.CONNECT_TIMEOUT))
        autocommit = bool(config.get(_.AUTOCOMMIT, cls.DEFAULT.AUTOCOMMIT))

        postgres_config = PostgresConfigDriver(
            connection_url, connect_timeout, autocommit
        )

        if resolver:
            return PostgresUnresolvedConfigDriver(
                name, resolver, postgres_config, properties
            )
        else:
            return PostgresResolvedConfigDriver(name, postgres_config)
