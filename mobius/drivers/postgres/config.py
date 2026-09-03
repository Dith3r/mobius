from __future__ import annotations

from typing import Any, Dict
from urllib.parse import quote_plus

from mobius.commons.data import mask_url_credentials
from mobius.commons.mapping import InvalidValueError, ObjectContext
from mobius.drivers.manager import (
    CommonDriverMapper,
    DriverResolvedConfig,
    DriverUnresolvedConfig,
    IConfigDriverMapper,
    IDriverConfig,
)
from mobius.drivers.postgres.driver import PostgresDriver


class PostgresConfigDriver(IDriverConfig):
    connection_url: str | None
    connect_timeout: int
    autocommit: bool

    def __init__(
        self,
        connection_url: str | None,
        connect_timeout: int,
        autocommit: bool,
    ):
        self.connection_url = connection_url
        self.connect_timeout = connect_timeout
        self.autocommit = autocommit

    def __str__(self):
        url = mask_url_credentials(self.connection_url) if self.connection_url else None
        return (
            f"{self.__class__.__name__}[connection_url={url}, "
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
    def from_context(
        cls, name: str, context: ObjectContext
    ) -> IDriverConfig | None:
        _ = cls.FIELDS

        resolver = context.find_string(_.RESOLVER).or_none()
        properties = context.find_string_map(_.PROPERTIES).or_else({})

        def read_config(config: ObjectContext) -> PostgresConfigDriver | None:
            connection_url = config.get_string(_.CONNECTION_URL)
            connect_timeout = (
                config.find_int(_.CONNECT_TIMEOUT)
                .must(
                    InvalidValueError(reason="must be positive"),
                    lambda value: value > 0,
                )
                .or_else(cls.DEFAULT.CONNECT_TIMEOUT)
            )
            autocommit = config.find_bool(_.AUTOCOMMIT).or_else(
                cls.DEFAULT.AUTOCOMMIT
            )

            return config.construct(
                lambda: PostgresConfigDriver(
                    connection_url.require(), connect_timeout, autocommit
                )
            )

        postgres_config = context.get_object(_.CONFIG, read_config).or_none()
        if postgres_config is None:
            return None

        if resolver:
            return PostgresUnresolvedConfigDriver(
                name, resolver, postgres_config, properties
            )

        return PostgresResolvedConfigDriver(name, postgres_config)
